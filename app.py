#!/usr/bin/env python3
from flask import Flask, render_template, request, redirect, send_from_directory, jsonify
from urllib.parse import quote
from backend import process_data, WCAIDValueError, WCADataNotLoadedError, init_wca_data
import os
import traceback
import time
import re
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from io import BytesIO
import dotenv

dotenv_location = dotenv.find_dotenv()
if not dotenv_location:
    print('ERROR: please add a .env')
    print('run `cp .env.example .env` then edit .env to a proper configuration')
    exit(1)
dotenv.load_dotenv(dotenv_location)

ALLOWED_EXTENSIONS = {'txt', 'json', 'csv'}

PORT = int(os.environ.get('PORT', '5000'))
SECRET_KEY = os.environ.get('SECRET_KEY', 'super secret key !@#')
DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/uploads')

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.secret_key = SECRET_KEY
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# task store for processing data in the background
# structure: {task_id: {"status": "processing"|"success"|"error", "result": ..., "error": ..., "created_at": timestamp}}
_task_store = {}
_task_store_lock = threading.Lock() # use this whenever messing with task store
_executor = ThreadPoolExecutor(max_workers=4)
TASK_EXPIRY_SECONDS = 30 * 60 # 30min


def _cleanup_old_tasks():
    """remove tasks older than TASK_EXPIRY_SECONDS"""
    now = time.time()
    with _task_store_lock:
        expired = [tid for tid, task in _task_store.items() if now - task["created_at"] > TASK_EXPIRY_SECONDS]
        for tid in expired:
            del _task_store[tid]


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.template_filter('regex_replace_dom_id')
def regex_replace_dom_id(s):
    return re.sub(r'[^\w-]+', '', str(s))


@app.route('/', methods=['GET', 'POST'])
def index():
    # UPDATE: this logic for POSTs is no longer used, but we'll keep it here for redundancy
    # see /api/start-processing for new async logic
    # (error handling has been reworked to use GET param instead of flash())
    if request.method == 'POST':
        # check if the post request has the file part or textinput
        if 'file' not in request.files and request.form.get('textinput', '') == '':
            return redirect('/?error=' + quote('Please select a file or paste the data'))
        file = request.files.get('file', None)
        textdata = request.form.get('textinput', None)
        if textdata == '':
            textdata = None

        # if user does not select file, browser also
        # submit an empty part without filename
        if file and file.filename == '' and not textdata:
            return redirect('/?error=' + quote('Please select a file or paste the data'))
        if file and not allowed_file(file.filename):
            return redirect('/?error=' + quote('Looks like this timer\'s data is not supported yet. '
                         'Please open an issue on the '
                         '<a href="https://github.com/anton-3/kuebiko-cubing/issues">github page</a>'
                         ' and upload the file there.'))
        if (file and allowed_file(file.filename)) or textdata:
            if file:
                file_to_send = file.stream
            else:
                file_to_send = BytesIO(textdata.encode())

            chart_by = request.form.get('chart-by', 'chart-by-dates')
            secondary_y_axis = request.form.get('secondary-y-axis', 'none')
            subx_threshold_mode = request.form.get('subx-threshold', 'auto')
            subx_override = request.form.get('subx-override', 'none')
            day_end_hour = request.form.get('day-end-hour', 3, type=int)
            trim_percentage = request.form.get('trim-percentage', 5, type=int)
            merge_sessions = request.form.get('merge-sessions', 'merge-sessions-no')
            timezone = request.form.get('tz', 'UTC')

            if secondary_y_axis == 'none':
                secondary_y_axis = None

            if merge_sessions == 'merge-sessions-yes':
                merge_sessions = True
            else:
                merge_sessions = False

            # noinspection PyBroadException
            try:
                solves_details, overall_pbs, solves_by_dates, timer_type, datalen = \
                    process_data(file_to_send, chart_by, secondary_y_axis, subx_threshold_mode, subx_override,
                                 day_end_hour, timezone, trim_percentage, merge_sessions)
                return render_template("data.html", solves_details=solves_details, overall_pbs=overall_pbs,
                                       solves_by_dates=solves_by_dates, timer_type=timer_type, datalen=datalen)
            except NotImplementedError:
                return redirect('/?error=' + quote('Looks like this file type is not supported yet. '
                             'Please open an issue on the '
                             '<a href="https://github.com/anton-3/kuebiko-cubing/issues">github page</a>'
                             ' and upload the file there.'))
            except WCADataNotLoadedError:
                return redirect('/?error=' + quote('Unable to retrieve WCA data, please try again later.'))
            except WCAIDValueError:
                return redirect('/?error=' + quote('WCA ID not found'))
            except Exception:
                if not app.debug:
                    error_msg = ('Something went wrong while reading the file. '
                                 'Please open an issue on the '
                                 '<a href="https://github.com/anton-3/kuebiko-cubing/issues">github page</a>'
                                 ' and upload the file there.')
                    timestr = time.strftime("%Y%m%d_%H%M%S_")
                    if file:
                        filename = timestr + secure_filename(file.filename)
                    else:
                        filename = timestr + "textarea"
                    file_to_send.seek(0)
                    with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'wb') as data_file:
                        data_file.write(file_to_send.read())

                    err_filename = filename + '_err'
                    with open(os.path.join(app.config['UPLOAD_FOLDER'], err_filename), 'w') as err_file:
                        err_file.write(traceback.format_exc())
                    return redirect('/?error=' + quote(error_msg))
                else:
                    raise
    return render_template("index.html")


def _run_process_data(task_id, file_bytes, filename, chart_by, secondary_y_axis,
                      subx_threshold_mode, subx_override, day_end_hour, timezone,
                      trim_percentage, merge_sessions):
    """Background worker function to process data and update task store"""
    try:
        file_to_send = BytesIO(file_bytes)
        solves_details, overall_pbs, solves_by_dates, timer_type, datalen = \
            process_data(file_to_send, chart_by, secondary_y_axis, subx_threshold_mode,
                         subx_override, day_end_hour, timezone, trim_percentage, merge_sessions)

        with _task_store_lock:
            _task_store[task_id]["status"] = "success"
            _task_store[task_id]["result"] = {
                "solves_details": solves_details,
                "overall_pbs": overall_pbs,
                "solves_by_dates": solves_by_dates,
                "timer_type": timer_type,
                "datalen": datalen
            }
    except NotImplementedError:
        with _task_store_lock:
            _task_store[task_id]["status"] = "error"
            _task_store[task_id]["error"] = ('Looks like this file type is not supported yet. '
                'Please open an issue on the '
                '<a href="https://github.com/anton-3/kuebiko-cubing/issues">github page</a>'
                ' and upload the file there.')
    except WCADataNotLoadedError:
        with _task_store_lock:
            _task_store[task_id]["status"] = "error"
            _task_store[task_id]["error"] = 'Unable to retrieve WCA data, please try again later.'
    except WCAIDValueError:
        with _task_store_lock:
            _task_store[task_id]["status"] = "error"
            _task_store[task_id]["error"] = 'WCA ID not found'
    except Exception:
        error_msg = ('Something went wrong while reading the file. '
                     'Please open an issue on the '
                     '<a href="https://github.com/anton-3/kuebiko-cubing/issues">github page</a>'
                     ' and upload the file there.')
        with _task_store_lock:
            _task_store[task_id]["status"] = "error"
            _task_store[task_id]["error"] = error_msg

        if not app.debug:
            try:
                timestr = time.strftime("%Y%m%d_%H%M%S_")
                safe_filename = timestr + (secure_filename(filename) if filename else "textarea")
                with open(os.path.join(app.config['UPLOAD_FOLDER'], safe_filename), 'wb') as data_file:
                    data_file.write(file_bytes)
                err_filename = safe_filename + '_err'
                with open(os.path.join(app.config['UPLOAD_FOLDER'], err_filename), 'w') as err_file:
                    err_file.write(traceback.format_exc())
            except Exception:
                pass


@app.route('/api/start-processing', methods=['POST'])
def api_start_processing():
    """Start async processing of uploaded data, returns task_id"""
    _cleanup_old_tasks()

    if 'file' not in request.files and request.form.get('textinput', '') == '':
        return jsonify({"error": "Please select a file or paste the data"}), 400

    file = request.files.get('file', None)
    textdata = request.form.get('textinput', None)
    if textdata == '':
        textdata = None

    if file and file.filename == '' and not textdata:
        return jsonify({"error": "Please select a file or paste the data"}), 400

    if file and file.filename and not allowed_file(file.filename):
        return jsonify({"error": "Looks like this timer's data is not supported yet. "
                       "Please open an issue on the github page and upload the file there."}), 400

    if not ((file and file.filename and allowed_file(file.filename)) or textdata):
        return jsonify({"error": "Please select a file or paste the data"}), 400

    if file and file.filename:
        file_bytes = file.read()
        filename = file.filename
    else:
        file_bytes = textdata.encode()
        filename = None

    chart_by = request.form.get('chart-by', 'chart-by-dates')
    secondary_y_axis = request.form.get('secondary-y-axis', 'none')
    subx_threshold_mode = request.form.get('subx-threshold', 'auto')
    subx_override = request.form.get('subx-override', 'none')
    day_end_hour = request.form.get('day-end-hour', 3, type=int)
    trim_percentage = request.form.get('trim-percentage', 5, type=int)
    merge_sessions = request.form.get('merge-sessions', 'merge-sessions-no')
    timezone = request.form.get('tz', 'UTC')

    if secondary_y_axis == 'none':
        secondary_y_axis = None
    merge_sessions = (merge_sessions == 'merge-sessions-yes')

    task_id = str(uuid.uuid4())
    with _task_store_lock:
        _task_store[task_id] = {
            "status": "processing",
            "created_at": time.time(),
            "result": None,
            "error": None
        }

    _executor.submit(_run_process_data, task_id, file_bytes, filename, chart_by,
                     secondary_y_axis, subx_threshold_mode, subx_override,
                     day_end_hour, timezone, trim_percentage, merge_sessions)

    return jsonify({"task_id": task_id})


@app.route('/api/task-status/<task_id>', methods=['GET'])
def api_task_status(task_id):
    """poll for the status of a processing task. if success, the frontend will redirect to the results"""
    with _task_store_lock:
        task = _task_store.get(task_id)

    if task is None:
        return jsonify({"status": "error", "message": "Task not found or expired"}), 404

    if task["status"] == "processing":
        return jsonify({"status": "processing"})
    elif task["status"] == "success":
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": task["error"]})


@app.route('/data/<task_id>', methods=['GET'])
def data_result(task_id):
    """after a data processing task is done, this page shows the results"""
    with _task_store_lock:
        print(_task_store.keys(), flush=True)
        task = _task_store.get(task_id)
    
    if task is None:
        return redirect('/?error=' + quote('Results not found or expired. Please submit your solves again.'))
    
    if task["status"] != "success":
        return redirect('/?error=' + quote('Results not ready yet or processing failed.'))

    result = task["result"]
    return render_template("data.html",
                           solves_details=result["solves_details"],
                           overall_pbs=result["overall_pbs"],
                           solves_by_dates=result["solves_by_dates"],
                           timer_type=result["timer_type"],
                           datalen=result["datalen"])


# noinspection PyUnusedLocal
@app.errorhandler(413)
def request_entity_too_large(e):
    error_msg = ('The file is too large. '
                 'If the file is truly valid, please open an issue on the '
                 '<a href="https://github.com/anton-3/kuebiko-cubing/issues">github page</a>'
                 ' and upload the file there.')
    return redirect('/?error=' + quote(error_msg))


if __name__ == '__main__':
    init_wca_data() # for WCA ID lookups from WCA_export.tsv.zip

    if DEBUG:
        app.run(debug=True, host='0.0.0.0', port=PORT) # docker seems to require host 0.0.0.0
    else:
        from waitress import serve
        print(f'Starting production Waitress server on 0.0.0.0:{PORT}', flush=True)
        serve(app, port=PORT, trusted_proxy='*', trusted_proxy_headers='x-forwarded-for x-forwarded-proto x-forwarded-host x-forwarded-port')
