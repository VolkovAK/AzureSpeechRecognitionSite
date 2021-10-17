import os
import time
from flask import (
    Flask, 
    Response, 
    render_template,
    make_response, 
    request, 
    url_for, 
    jsonify, 
    redirect,
    flash,
    send_from_directory
)
from werkzeug.utils import secure_filename

from tasks import celery_app 
from database import create_table_if_not_exists, get_all_records_sort_date


ALLOWED_EXTENSIONS = ["mov", "mp4", "mkv", "mp3", "acc", "ogg", "m4a", "wav"]
flask_app = Flask("main_app")
flask_app.config['UPLOAD_FOLDER'] = "./uploads/"
flask_app.config['SESSION_TYPE'] = 'filesystem'


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@flask_app.route('/download/<path:filename>', methods=['GET', 'POST'])
def download(filename):
    file_name = os.path.splitext(filename)[0] + ".txt"
    directory = os.path.join(flask.root_path, 'results')
    return send_from_directory(directory, file_name)


@flask_app.route("/", methods=["GET", "POST"])
def index() -> Response:
    if request.method == "GET":
        db_data = get_all_records_sort_date()
        table_data = [{"submit_datetime": r[1], "name": r[2], "duration": r[3], "status": r[4]} for r in db_data]
        return render_template("index.html", items=table_data)
    if request.method == "POST":
        # check if the post request has the file part
        if 'file' not in request.files:
            print('No file part')
            return redirect(request.url)
        uploaded_file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if uploaded_file.filename == '':
            print('No selected file')
            return redirect(request.url)
        if uploaded_file and allowed_file(uploaded_file.filename):
            filename = secure_filename(uploaded_file.filename)
            save_path = os.path.join(flask_app.config['UPLOAD_FOLDER'], filename)
            uploaded_file.save(save_path)
            print(filename)
            celery_app.send_task("transcribe", args=[save_path, flask_app.config["AZURE_SUB"]])
            return redirect(request.url)
    print(request.method)
    return jsonify("OK")


def main():
    flask_app.secret_key = 'super secret key'
    with open("/run/secrets/azure_key") as f:
        flask_app.config["AZURE_SUB"] = f.read().strip()
    create_table_if_not_exists()

    flask_app.run(host="0.0.0.0", port=5000)


if __name__ == "__main__":
    main()