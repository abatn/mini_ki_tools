try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.executors.pool import ThreadPoolExecutor
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
    BackgroundScheduler = None
    ThreadPoolExecutor = None

try:
    from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    SQLAlchemyJobStore = None

from flask import Flask, request, jsonify

# Konfiguration des Schedulers
if SCHEDULER_AVAILABLE:
    if SQLALCHEMY_AVAILABLE:
        jobstores = {
            'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
        }
    else:
        # Use memory jobstore as fallback
        from apscheduler.jobstores.memory import MemoryJobStore
        jobstores = {
            'default': MemoryJobStore()
        }
    
    executors = {
        'default': ThreadPoolExecutor(20) if ThreadPoolExecutor else {}
    }
    
    scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors)
else:
    scheduler = None

app = Flask(__name__)

@app.route('/api/schedule/add', methods=['POST'])
def add_job():
    if not SCHEDULER_AVAILABLE:
        return jsonify({'status': 'error', 'message': 'Scheduler not available'}), 500
    data = request.json
    job_id = scheduler.add_job(func=data['func'], args=data.get('args', ()), kwargs=data.get('kwargs', {}), id=data['id'])
    return jsonify({'status': 'success', 'job_id': job_id.id})

@app.route('/api/schedule/list', methods=['GET'])
def list_jobs():
    if not SCHEDULER_AVAILABLE:
        return jsonify({'jobs': []})
    jobs = [job.id for job in scheduler.get_jobs()]
    return jsonify({'jobs': jobs})

@app.route('/api/schedule/remove', methods=['POST'])
def remove_job():
    if not SCHEDULER_AVAILABLE:
        return jsonify({'status': 'error', 'message': 'Scheduler not available'}), 500
    data = request.json
    job_id = data['id']
    scheduler.remove_job(job_id)
    return jsonify({'status': 'success', 'job_id': job_id})

if __name__ == '__main__':
    if SCHEDULER_AVAILABLE:
        scheduler.start()
    app.run(debug=True)