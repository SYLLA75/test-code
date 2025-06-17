"""Minimal Flask UI for Kubernetes deployment."""
from __future__ import annotations

from flask import Flask, render_template, request, redirect, url_for, Response
import subprocess
from pathlib import Path

APP = Flask(__name__)
CONFIG_PATH = Path('../ansible/config.yml')


def run_playbook() -> subprocess.Popen:
    """Run the main playbook using ansible-runner."""
    cmd = [
        'ansible-playbook',
        '-i', '../ansible/inventory.ini',
        '../ansible/site.yml',
    ]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


@APP.route('/')
def index() -> str:
    config_data = CONFIG_PATH.read_text()
    return render_template('index.html', config=config_data)


@APP.route('/save', methods=['POST'])
def save() -> Response:
    CONFIG_PATH.write_text(request.form['config'])
    return redirect(url_for('index'))


@APP.route('/deploy')
def deploy() -> Response:
    process = run_playbook()

    def generate() -> str:
        for line in process.stdout:
            yield f"data: {line}\n\n"
    return Response(generate(), mimetype='text/event-stream')


@APP.route('/destroy')
def destroy() -> Response:
    cmd = ['ansible-playbook', '-i', '../ansible/inventory.ini', '../ansible/cleanup.yml']
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    def generate() -> str:
        for line in process.stdout:
            yield f"data: {line}\n\n"
    return Response(generate(), mimetype='text/event-stream')


if __name__ == '__main__':
    APP.run(debug=True, port=5000)
