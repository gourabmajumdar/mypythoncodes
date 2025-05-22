import tempfile

from celery.result import AsyncResult
from celery.result import shared_task

from cca_pbv.library.extra_vars import ExtraVars
from cca_pbv.library.models.extra_vars_models import ExtraVarsMongoSearchCriteria
from cca_pbv.library.models.report_models import ReportResponse
from cca_pbv.library.models.toolkit import ToolkitAPI
from cca_pbv.library.report import ReportService, generate_report_data
from cca_pbv.library.mail import ReportEmail
from cca_pbv.library.modules import VmwareModule
from cca_pbv.library.baseline import BaselineConfig
from cca_pbv.workers.builder import (
    TaskName,
    get_builder,
    extract_results_from_data_collection,
)

from cca_pbv.library.validations.cluster import ESXiValidator
from cca_pbv.library.validations.vcenter import VcenterValidator
from cca_pbv.library.validations.esxi import ESXiHostValidator
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(name=TaskName.EXECUTE_REPORT, bind=True)
def report(self, request):
    data = generate_report_data(request)
    report_type = request["report_type"]
    
    logger.info("Creating PBV report with data: %s", data)

    builder = get_builder(report_type, data, self.env.get_else("rabbit_mq_query", "celery"))

   (builder.build() >> builder.run).expects("Error executing PBV report")

    host_id = request["host"]
    order_id = request["order_id"]

    logger.info("Report succesfully initiated with report, id: %s", order_id)
    return ReportResponse(
        status="success",
        message=f{request["report_type"] report generated for {request["host"],
        order_id=order_id
    ).model_dump()


@shared_task(name=TaskName.CREATE_INITIAL_REPORT, bind=True)
def create_initial_report(self, data):
    report_service = ReportService()
    report = report_service.create_report(data=data)
    return created_report


@shared_task(name=TaskName.UPDATE_REPORT_STATUS, bind=True)
def update_report_status(self, task_id, data, status, *args, **kwargs):
    task_name = self.name
    if task_id:
        res = AsyncResult(task_id)
        
    report_tracker = ReportService()
    report_tracker.update_report_state(data["order_id"], status, task_name)


@shared_task(name=TaskName.SAVE_METADATA, bind=True)
def save_metadata(self, data_results, data):
    extra_vars_dump, baseline_config = extract_results_from_data_collection(data_results)
    baseline_config, baseline_version = baseline
    extra_vars = ExtraVars()
    extra_vars.load(json_string=str(extra_vars_dump))
    
    metadata = {
        "vcenter_version": extra_vars.get_vcsa_version(),
        "cluster_info": extra_vars.get_clusters(),
        "baseline_version": baseline_version,
    }

    report_service = ReportService()
    report_service.update_report_metadata(
        data["order_id"], metadata, self.name.value
    ).expects("Report metadata failed to update.")

    return extra_vars_dump, baseline_config, metadata


@shared_task(name=TaskName.RETRIEVE_EXTRA_VARS, bind=True)
def retrieve_extra_vars(self, data):
    extra_vars = ExtraVars()
    mongo_params = ExtraVarsMongoSearchCriteria(
        vcenter=data["request"]["host"],
        job_id=data["request"].get("job_id")
    )
    extra_vars.load(mongo=mongo_params)
    return extra_vars.dump()


@shared_task(name=TaskName.RETRIEVE_VSPHERE_CONFIG, bind=True)
def retrieve_vsphere_config(self):
    baseline = BaselineConfig(self.env)
    baseline.pull().expects("Baseline error")
    encoded_version = baseline.get_baseline_version()
    baseline_version = (
        encoded_version.decode()
        if encoded_version
        else self.env.get_else("bitbucket_branch", "")
    )
    config_tree = baseline.parse().expects("Baseline error")

    print(baseline_version)
    return config_tree, baseline_version

@shared_task(name=TaskName.SEND_PBV_REPORT, bind=True)
def send_pbv_report(self, *args, **kwargs):
    data = kwargs.get("data")
    toolkit = ToolKitAPI(self.env)
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        email = ReportEmail(self.env, toolkit)
        create, msg = email.create(data, tmp_dir)
        if not create:
            logger.warning("Failed to create report email due to: %s", msg)
            raise Exception(msg)
        return email.send()


@shared_task(name=TaskName.CLUSTER_MODULE, bind=True)
def cluster_module(self, data_results, data):
    params = {"cluster_name": data["request"]["target_cluster"]}
    baseline, extra_vars = extract_results_from_data_collection(data_results)
    return run_vmware_module(baseline, extra_vars, data, VmwareModule, ESXiValidator, params)

@shared_task(name=TaskName.VCENTER_MODULE, bind=True)
def vcenter_module(self, data_results, data):
    baseline, extra_vars = extract_results_from_data_collection(data_results)
    return run_vmware_module(baseline, extra_vars, data, VmwareModule, VcenterValidator, {})

@shared_task(name=TaskName.ESXI_MODULE, bind=True)
def esxi_module(self, data_results, data):
    params = {"cluster_name": data["request"]["target_cluster"]}
    baseline, extra_vars = extract_results_from_data_collection(data_results)
    return run_vmware_module(baseline, extra_vars, data, VmwareModule, ESXiHostValidator, params)

def run_vmware_module(baseline, extra_vars, data, module, validator, params):
    host = data["request"]["host"]
    extra_vars_class = ExtraVars()
    extra_vars_class.load(json_string=str(extra_vars))
    module_data = data.copy()
    module_data.update({"extra_vars": extra_vars_class})
    module = module(
        baseline=baseline,
        data=module_data,
        host=host,
        params=params,
    )

    saved = module.run(validator) >> module.save
    return saved.expects("Module run failed")
