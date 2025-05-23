from flask import Flask, render_template, request, Response, stream_with_context
import subprocess
import os
import time

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Get form input
        appliance_type = request.form.get('appliance_type')
        job_env = request.form.get('job_env')
        model_type = request.form.get('model_type')
        job_type = request.form.get('job_type')
        pnics = request.form.get('pnics')
        agora_enable = request.form.get('agora_enable')
        BACCON = request.form.get('BACCON') or None
        destroy = request.form.get('destroy') or 'yes'
        extra_vars_file = request.form.get('extra_vars_file') or None
        scm_branch = request.form.get('scm_branch') or None
        baseline_branch = request.form.get('baseline_branch') or None
        skip_types = request.form.getlist('skip_types')  # List of selected values

        # Determine the script to run based on the appliance type
        if appliance_type == "vCenter":
            job_type = request.form.get('vcenter_type')
            vcsa_version = request.form.get('vcsa_version')
            script_name = "test_vcenter_automation.py"
        else:
            script_name = "test_cluster_automation.py"

        # Construct the command
        command = [
            "python", script_name,
            "--job_env", job_env,
            "--job_type", job_type,
            "--destroy", destroy
        ]

        # Add optional arguments only if they are not None
        if appliance_type == "vCenter":
            if vcsa_version:
                command.extend(["--vcsa_ver", vcsa_version])
        else:
            if BACCON:
                command.extend(["--BACCON", BACCON])
            if agora_enable:
                command.extend(["--agora", agora_enable])
            if pnics:
                command.extend(["--pnics", pnics])
            if model_type:
                command.extend(["--model_type", model_type])
            if skip_types:
                command.extend(["--skip_types"] + skip_types)
            if extra_vars_file:
                command.extend(["--extra_vars_file", extra_vars_file])
            if scm_branch:
                command.extend(["--scm_branch", scm_branch])
            if baseline_branch:
                command.extend(["--baseline_branch", baseline_branch])

        # Debug print to show the constructed command
        print(f"Running command: {' '.join(map(str, command))}")

        # Execute the Python script with subprocess
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        log_filename = "logfile.txt"
        if os.path.exists(log_filename):
            with open(log_filename, 'r') as logfile:
                logfile_content = logfile.read()
        else:
            logfile_content = 'logfile does not exist'

        # Print stdout and stderr for debugging
        print(f"Standard Output: {stdout.decode('utf-8')}")
        print(f"Standard Error: {stderr.decode('utf-8')}")

        # Return the output
        result = {
            'stdout': stdout.decode('utf-8'),
            'stderr': stderr.decode('utf-8'),
            'returncode': process.returncode,
            'logfile_content': logfile_content
        }

        return render_template('index.html', result=result)

    return render_template('index.html', result=None)

# New route to stream log file content
@app.route('/stream_logs')
def stream_logs():
    from test_cluster_automation import log_filename

    def generate():
        with open(log_filename, 'r') as logfile:
            logfile.seek(0, os.SEEK_END)  # Move cursor to the end of the file
            while True:
                line = logfile.readline()
                if not line:
                    time.sleep(1)
                    continue
                yield f"data: {line}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
