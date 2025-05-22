from unittest.mock import patch, MagicMock
import pytest
from celery import Celery

from cca_pbv.library.environment import Envars
from cca_pbv.library.hashivault import Hashivault
from cca_pbv.application_container import Application
from cca_pbv.library.models.report_models import ReportResponse
from cca_pbv.library.result import Ok, Err
from cca_pbv.workers.tasks import (
    report,
    esxi_module,
    vcenter_module,
    cluster_module,
    retrieve_vsphere_config,
    save_metadata,
)
from cca_pbv.workers.base import BaseTask


@pytest.fixture()
def container():
    container = Application()
    hashi_mock = MagicMock(spec=Hashivault)
    envars_mock = MagicMock(spec=Envars)
    container.core.hashi.override(hashi_mock)
    container.core.environment.override(envars_mock)
    container.wire(modules=["cca_pbv.workers.base"])
    yield container, hashi_mock, envars_mock
    container.unwire()


@pytest.fixture()
def test_celery_app(container):
    app = Celery()
    app.conf.update(
        broker_url="memory://",
        result_backend="cache+memory://",
        task_always_eager=True,
        task_eager_propagate=True,
    )
    app.task_cls = BaseTask
    return app


class TestTasks:

    @pytest.fixture(scope="function")
    def baseline_mock(self, test_celery_app, monkeypatch, container):
        monkeypatch.setattr(retrieve_vsphere_config, "app", test_celery_app)
        container, hashi_mock, envars_mock = container
        envars_mock.check_all.return_value = True, None
        envars_mock.variables = {
            "bitbucket_host": "bitbucket_host",
            "bitbucket_repo": "bitbucket_repo",
            "bitbucket_branch": "bitbucket_branch",
            "bitbucket_user": "user",
            "bitbucket_token": "token",
        }
        yield

    @patch("cca_pbv.library.baseline.BaselineConfig.pull")
    @patch("cca_pbv.library.baseline.BaselineConfig.parse")
    @patch("cca_pbv.library.baseline.BaselineConfig.get_baseline_version")
    def test_retrieve_vsphere_config_success(
        self, baseline_version, baseline_parse, baseline_pull, baseline_mock
    ):
        baseline_pull.return_value = Ok(True)
        baseline_parse.return_value = Ok({})
        baseline_version.return_value = b"test"
        result = retrieve_vsphere_config.delay()
        assert result.get() == ({}, "test")

    @patch("cca_pbv.library.baseline.BaselineConfig.pull")
    def test_retrieve_vsphere_config_failed_pull(
        self, baseline_pull, baseline_mock, test_celery_app
    ):
        baseline_pull.return_value = Err("Failed to pull")
        with pytest.raises(Exception) as excinfo:
            retrieve_vsphere_config.delay().get()
        assert "Failed to pull" in str(excinfo.value)

    @patch("cca_pbv.library.baseline.BaselineConfig.pull")
    @patch("cca_pbv.library.baseline.BaselineConfig.parse")
    @patch("cca_pbv.library.baseline.BaselineConfig.get_baseline_version")
    def test_retrieve_vsphere_config_failed_parse(
        self, baseline_version, baseline_parse, baseline_pull, baseline_mock, test_celery_app
    ):
        baseline_pull.return_value = Ok(True)
        baseline_parse.return_value = Err("error parsing")
        baseline_version.return_value = b"test"
        with pytest.raises(Exception) as excinfo:
            retrieve_vsphere_config.delay().get()
        assert "Baseline error: error parsing" in str(excinfo.value)

    @patch("cca_pbv.workers.builder.Builder.run")
    def test_execute_report_success_expect_order_id(self, builder_run, envars, monkeypatch, test_celery_app):
        monkeypatch.setattr(report, "app", test_celery_app)
        builder_run.return_value = Ok(True)
        request = self.get_dummy_payload()
        result = report.delay(request).get()
        assert ReportResponse.model_validate_json(result)

    @patch("cca_pbv.workers.builder.Builder.run")
    def test_execute_report_error_expect_message(self, builder_run, monkeypatch, test_celery_app):
        monkeypatch.setattr(report, "app", test_celery_app)
        builder_run.return_value = Err("error_message")
        request = self.get_dummy_payload()
        with pytest.raises(Exception) as excinfo:
            report(request).get()
        assert "Error executing PBV report: error_message" in str(excinfo.value)

    @patch("cca_pbv.workers.builder.Builder.build")
    def test_execute_report_error_expect_message_build(self, builder_build, monkeypatch, test_celery_app):
        monkeypatch.setattr(report, "app", test_celery_app)
        builder_build.return_value = Err("error_message_build")
        request = self.get_dummy_payload()
        with pytest.raises(Exception) as excinfo:
            report(request).get()
        assert "Error executing PBV report: error_message_build" in str(excinfo.value)

    @patch("cca_pbv.library.extra_vars.ExtraVars.load")
    @patch("cca_pbv.library.modules.VmwareModule.run")
    @patch("cca_pbv.library.modules.VmwareModule.save")
    def test_esxi_module_success(self, vmware_module_save, vmware_module_run, extra_vars_load, monkeypatch, test_celery_app):
        monkeypatch.setattr(esxi_module, "app", test_celery_app)
        data = {
            "request": {
                "target_cluster": "EXAMPLE_CLUSTER_NAME",
                "host": "hostname.sdi.corp.bankofamerica.com"
            }
        }
        result = self.module_run(vmware_module_save, vmware_module_run, extra_vars_load, esxi_module, data)
        assert result is True

    @patch("cca_pbv.library.extra_vars.ExtraVars.load")
    @patch("cca_pbv.library.modules.VmwareModule.run")
    @patch("cca_pbv.library.modules.VmwareModule.save")
    def test_vcenter_module_success(self, vmware_module_save, vmware_module_run, extra_vars_load, monkeypatch, test_celery_app):
        monkeypatch.setattr(vcenter_module, "app", test_celery_app)
        data = {
            "request": {
                "target_cluster": "EXAMPLE_CLUSTER_NAME",
                "host": "hostname.sdi.corp.bankofamerica.com"
            }
        }
        result = self.module_run(vmware_module_save, vmware_module_run, extra_vars_load, vcenter_module, data)
        assert result is True

    @patch("cca_pbv.library.extra_vars.ExtraVars.load")
    @patch("cca_pbv.library.modules.VmwareModule.run")
    @patch("cca_pbv.library.modules.VmwareModule.save")
    def test_cluster_module_success(self, vmware_module_save, vmware_module_run, extra_vars_load, monkeypatch, test_celery_app):
        monkeypatch.setattr(cluster_module, "app", test_celery_app)
        data = {
            "request": {
                "target_cluster": "EXAMPLE_CLUSTER_NAME",
                "host": "hostname.sdi.corp.bankofamerica.com"
            }
        }
        result = self.module_run(vmware_module_save, vmware_module_run, extra_vars_load, cluster_module, data)
        assert result is True

    def module_run(self, vmware_module_save, vmware_module_run, extra_vars_load, task, data):
        extra_vars = {}
        baseline = {}
        results = [extra_vars, baseline]
        vmware_module_run.return_value = Ok({})
        vmware_module_save.return_value = Ok(True)
        extra_vars_load.return_value = {}
        result = task.delay(results, data)
        return result.get()

    @patch("cca_pbv.library.extra_vars.ExtraVars.load")
    @patch("cca_pbv.library.modules.VmwareModule.run")
    def test_cluster_module_fail(self, vmware_module_run, extra_vars_load, monkeypatch, test_celery_app):
        monkeypatch.setattr(cluster_module, "app", test_celery_app)
        extra_vars_load.return_value = {}
        vmware_module_run.return_value = Err("Failure to run module")
        data = {
            "request": {
                "target_cluster": "EXAMPLE_CLUSTER_NAME",
                "host": "hostname.sdi.corp.bankofamerica.com"
            }
        }
        extra_vars = {}
        baseline = {}
        results = [extra_vars, baseline]
        with pytest.raises(Exception) as excinfo:
            cluster_module.delay(results, data).get()
        assert "Failure to run module" in str(excinfo.value)

    def get_dummy_payload(self):
        request = {
            "host": "testhost.sdi.corp.bankofamerica.com",
            "target_cluster": "target_cluster",
            "nbkid": "nbkid",
            "order_id": "mock_order_id",
            "report_type": "cluster"
        }
        return request

    @patch("cca_pbv.workers.tasks.ReportService")
    @patch("cca_pbv.workers.tasks.extract_results_from_data_collection")
    @patch("cca_pbv.workers.tasks.ExtraVars")
    def test_save_metadata(self, mock_extra_vars, mock_extract_results, mock_result_service, test_celery_app):
        mock_baseline = ("baseline_config", "baseline_version")
        data = {"order_id": "dummy_test_id"}

        mock_extra_vars_instance = mock_extra_vars.return_value
        mock_extra_vars_instance.get_vcsa_version.return_value = "vcenter_version"
        mock_extra_vars_instance.get_clusters.return_value = "cluster_info"
        mock_extra_vars_instance.return_value.load.return_value = {}
        mock_extract_results.return_value = (mock_baseline, "mock_extra_var")

        mock_result_service.update_report_metadata.return_value = Ok(True)

        data_results = ["dummy_data", ("dummy_baseline_data", "dummy_baseline_version")]
        extra_var_return, baseline_config, metadata = save_metadata(data_results, data)

        assert baseline_config == "baseline_config"
        assert extra_var_return == "mock_extra_var"
        assert metadata.get("baseline_version") == "baseline_version"
        assert metadata.get("vcenter_version") == "vcenter_version"
        assert metadata.get("cluster_info") == "cluster_info"
