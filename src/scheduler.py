from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from flask import Flask, request, jsonify

# Konfiguration des Schedulers
jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
}
executors = {
    'default': ThreadPoolExecutor(20)
}
app = Flask(__name__)
scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors)

@app.route('/api/schedule/add', methods=['POST'])
def add_job():
    data = request.json
    job_id = scheduler.add_job(func=data['func'], args=data.get('args', ()), kwargs=data.get('kwargs', {}), id=data['id'])
    return jsonify({'status': 'success', 'job_id': job_id.id})

@app.route('/api/schedule/list', methods=['GET'])
def list_jobs():
    jobs = [job.id for job in scheduler.get_jobs()]
    return jsonify({'jobs': jobs})

@app.route('/api/schedule/remove', methods=['POST'])
def remove_job():
    data = request.json
    job_id = data['id']
    scheduler.remove_job(job_id)
    return jsonify({'status': 'success', 'job_id': job_id})

if __name__ == '__main__':
    scheduler.start()
    app.run(debug=True)