"""
Smart Adaptive File Compression System — Flask Application
Main entry point. Starts Flask server, background watcher, and compression scheduler.

Author: Gautam Chand
"""
import os
import sys
import threading
from flask import Flask, render_template, jsonify, request

from config import Config
from database import init_db, record_system_metrics
from monitor.watcher import FileWatcher
from monitor.scheduler import CompressionScheduler
from monitor.metadata_tracker import MetadataTracker
from ml.predictor import access_predictor

# API Blueprints
from api.dashboard import dashboard_bp
from api.compression import compression_bp
from api.folders import folders_bp
from api.analytics import analytics_bp


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__, 
                static_folder='static', 
                template_folder='templates')
    app.config.from_object(Config)
    
    # Register API blueprints
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(compression_bp)
    app.register_blueprint(folders_bp)
    app.register_blueprint(analytics_bp)
    
    # ── Page Routes ──────────────────────────────────────────
    
    @app.route('/')
    def dashboard():
        return render_template('dashboard.html')
    
    @app.route('/analytics')
    def analytics():
        return render_template('analytics.html')
    
    @app.route('/compression')
    def compression():
        return render_template('compression.html')
    
    @app.route('/settings')
    def settings():
        return render_template('settings.html')
    
    @app.route('/api/settings', methods=['GET', 'POST'])
    def handle_settings():
        if request.method == 'POST':
            data = request.get_json()
            Config.AUTO_COMPRESS_ENABLED = bool(data.get('auto_compress', Config.AUTO_COMPRESS_ENABLED))
            Config.SCHEDULER_INTERVAL_SECONDS = int(data.get('scheduler_interval', Config.SCHEDULER_INTERVAL_SECONDS))
            Config.HOT_RECENCY_HOURS = int(data.get('hot_hours', Config.HOT_RECENCY_HOURS))
            Config.HOT_ACCESS_COUNT = int(data.get('hot_count', Config.HOT_ACCESS_COUNT))
            Config.WARM_RECENCY_DAYS = int(data.get('warm_days', Config.WARM_RECENCY_DAYS))
            Config.WARM_ACCESS_COUNT = int(data.get('warm_count', Config.WARM_ACCESS_COUNT))
            Config.COLD_RECENCY_DAYS = int(data.get('cold_days', Config.COLD_RECENCY_DAYS))
            Config.COLD_ACCESS_COUNT = int(data.get('cold_count', Config.COLD_ACCESS_COUNT))
            
            # Restart scheduler with new interval if changed
            if app.scheduler:
                app.scheduler.interval = Config.SCHEDULER_INTERVAL_SECONDS
                
            return jsonify({'success': True, 'message': 'Settings saved successfully'})
            
        return jsonify({
            'auto_compress': Config.AUTO_COMPRESS_ENABLED,
            'scheduler_interval': Config.SCHEDULER_INTERVAL_SECONDS,
            'hot_hours': Config.HOT_RECENCY_HOURS,
            'hot_count': Config.HOT_ACCESS_COUNT,
            'warm_days': Config.WARM_RECENCY_DAYS,
            'warm_count': Config.WARM_ACCESS_COUNT,
            'cold_days': Config.COLD_RECENCY_DAYS,
            'cold_count': Config.COLD_ACCESS_COUNT,
            'monitor_folder': Config.DEFAULT_MONITOR_DIR
        })
    
    @app.route('/api/settings/reset-demo', methods=['POST'])
    def reset_demo():
        from database import get_db_connection
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM access_history")
            cursor.execute("DELETE FROM compression_log")
            cursor.execute("DELETE FROM system_metrics")
            cursor.execute("DELETE FROM recommendations")
            cursor.execute("DELETE FROM files")
            conn.commit()
        finally:
            conn.close()
        
        project_root = os.path.dirname(os.path.abspath(__file__))
        default_dir = os.path.normcase(os.path.abspath(os.path.join(project_root, 'monitored_folder')))
        current_dir = os.path.normcase(os.path.abspath(Config.DEFAULT_MONITOR_DIR))
        
        if current_dir == default_dir:
            if os.path.exists(current_dir):
                for f in os.listdir(current_dir):
                    fp = os.path.join(current_dir, f)
                    try:
                        if os.path.isfile(fp):
                            os.unlink(fp)
                    except Exception:
                        pass
        else:
            Config.DEFAULT_MONITOR_DIR = os.path.join(project_root, 'monitored_folder')
            current_dir = os.path.normcase(os.path.abspath(Config.DEFAULT_MONITOR_DIR))
            # Update watcher to default path
            if hasattr(app, 'file_watcher') and app.file_watcher:
                try:
                    app.file_watcher.change_folder(Config.DEFAULT_MONITOR_DIR)
                except Exception as e:
                    print(f"[ERROR] Failed to change watcher folder on reset: {e}")
                    
        os.makedirs(current_dir, exist_ok=True)
        sample_files = {
            'project_report.txt': 'This is a sample project report for the Smart Adaptive File Compression System.\n' * 100,
            'meeting_notes.txt': 'Meeting notes from the OS project discussion.\nTopics: File compression, scheduling, priority queues.\n' * 50,
            'data_analysis.csv': 'id,name,value,category\n' + '\n'.join(f'{i},item_{i},{i*10},cat_{i%5}' for i in range(500)),
            'config_backup.json': '{\n  "setting1": "value1",\n  "setting2": "value2"\n}\n' * 30,
            'old_readme.md': '# Old Project README\nThis file has not been accessed in a long time.\n' * 40,
            'debug_log.log': '[DEBUG] System initialized\n[INFO] Process started\n[WARN] Low memory\n' * 200,
            'user_data.xml': '<?xml version="1.0"?>\n<users>\n' + '\n'.join(f'  <user id="{i}"><name>User {i}</name></user>' for i in range(100)) + '\n</users>',
            'source_code.py': 'def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)\n\n' * 50,
            'styles.css': 'body { margin: 0; padding: 0; }\n.container { max-width: 1200px; }\n' * 80,
            'index.html': '<!DOCTYPE html>\n<html>\n<head><title>Sample</title></head>\n<body><h1>Hello World</h1></body>\n</html>\n' * 60,
        }
        import time
        file_ages = {
            'project_report.txt': 0.1,
            'styles.css': 0.2,
            'index.html': 0.3,
            'meeting_notes.txt': 2.0,
            'source_code.py': 4.0,
            'data_analysis.csv': 5.0,
            'config_backup.json': 12.0,
            'user_data.xml': 15.0,
            'old_readme.md': 45.0,
            'debug_log.log': 50.0,
        }
        # Stop watcher temporarily to prevent event interception
        watcher_was_running = False
        if hasattr(app, 'file_watcher') and app.file_watcher and app.file_watcher.is_running:
            app.file_watcher.stop()
            watcher_was_running = True

        for filename, content in sample_files.items():
            filepath = os.path.join(current_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            # Adjust filesystem access/modification times back in time
            age_days = file_ages.get(filename, 0.0)
            if age_days > 0.0:
                stale_time = time.time() - (age_days * 86400)
                os.utime(filepath, (stale_time, stale_time))
                
        MetadataTracker.scan_folder(current_dir)
        
        # Classify files and generate recommendations WITHOUT re-scanning
        if hasattr(app, 'scheduler') and app.scheduler:
            try:
                app.scheduler.generate_recommendations_only()
            except Exception as e:
                print(f"[ERROR] Failed to generate recommendations during reset: {e}")
                
        record_system_metrics()
        
        # Restart watcher if it was running
        if watcher_was_running and hasattr(app, 'file_watcher') and app.file_watcher:
            app.file_watcher.start()
            
        return jsonify({'success': True})
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        import traceback
        print("\n" + "="*80)
        print("[FLASK EXCEPTION RAISED]")
        traceback.print_exc()
        print("="*80 + "\n")
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

    # Initialize background service attributes on app object
    app.file_watcher = None
    app.scheduler = None

    # ── System Status API ────────────────────────────────────
    
    @app.route('/api/status')
    def system_status():
        return jsonify({
            'watcher': app.file_watcher.get_status() if app.file_watcher else {'is_running': False},
            'scheduler': app.scheduler.get_status() if app.scheduler else {'is_running': False},
            'ml': access_predictor.get_status(),
            'monitor_folder': Config.DEFAULT_MONITOR_DIR,
        })
    
    @app.route('/api/scheduler/run-now', methods=['POST'])
    def run_scheduler_now():
        if app.scheduler:
            result = app.scheduler.run_now(sync=True)
            return jsonify(result)
        return jsonify({'error': 'Scheduler not available'}), 500
    
    return app


def start_background_services(app):
    """Start file watcher and compression scheduler."""
    # Ensure directories exist
    Config.ensure_directories()
    
    # Initial folder scan
    print("\n[STARTUP] Scanning monitored folder...")
    scan_result = MetadataTracker.scan_folder()
    print(f"[STARTUP] Found {scan_result['scanned']} files")
    
    # Record initial metrics
    record_system_metrics()
    
    # Start file watcher
    app.file_watcher = FileWatcher(Config.DEFAULT_MONITOR_DIR)
    app.file_watcher.start()
    
    # Start compression scheduler
    app.scheduler = CompressionScheduler()
    app.scheduler.start()
    
    # Trigger an immediate scheduler cycle to populate recommendations on startup
    app.scheduler.run_now()
    
    # Try to load or train ML model
    if not access_predictor.load_model():
        access_predictor.train()
    
    print("[STARTUP] All background services started\n")


# ── Main ─────────────────────────────────────────────────────

app = create_app()

if __name__ == '__main__':
    print("=" * 60)
    print("  Smart Adaptive File Compression System")
    print("  OS Project - Gautam Chand")
    print("=" * 60)
    
    # Initialize database
    print("\n[STARTUP] Initializing database...")
    init_db()
    
    # Create sample files if monitored folder is empty
    monitor_dir = Config.DEFAULT_MONITOR_DIR
    os.makedirs(monitor_dir, exist_ok=True)
    
    if len(os.listdir(monitor_dir)) == 0:
        print("[STARTUP] Creating sample files for demonstration...")
        sample_files = {
            'project_report.txt': 'This is a sample project report for the Smart Adaptive File Compression System.\n' * 100,
            'meeting_notes.txt': 'Meeting notes from the OS project discussion.\nTopics: File compression, scheduling, priority queues.\n' * 50,
            'data_analysis.csv': 'id,name,value,category\n' + '\n'.join(f'{i},item_{i},{i*10},cat_{i%5}' for i in range(500)),
            'config_backup.json': '{\n  "setting1": "value1",\n  "setting2": "value2"\n}\n' * 30,
            'old_readme.md': '# Old Project README\nThis file has not been accessed in a long time.\n' * 40,
            'debug_log.log': f'[DEBUG] System initialized\n[INFO] Process started\n[WARN] Low memory\n' * 200,
            'user_data.xml': '<?xml version="1.0"?>\n<users>\n' + '\n'.join(f'  <user id="{i}"><name>User {i}</name></user>' for i in range(100)) + '\n</users>',
            'source_code.py': 'def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)\n\n' * 50,
            'styles.css': 'body { margin: 0; padding: 0; }\n.container { max-width: 1200px; }\n' * 80,
            'index.html': '<!DOCTYPE html>\n<html>\n<head><title>Sample</title></head>\n<body><h1>Hello World</h1></body>\n</html>\n' * 60,
        }
        
        import time
        file_ages = {
            'project_report.txt': 0.1,
            'styles.css': 0.2,
            'index.html': 0.3,
            'meeting_notes.txt': 2.0,
            'source_code.py': 4.0,
            'data_analysis.csv': 5.0,
            'config_backup.json': 12.0,
            'user_data.xml': 15.0,
            'old_readme.md': 45.0,
            'debug_log.log': 50.0,
        }
        for filename, content in sample_files.items():
            filepath = os.path.join(monitor_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            # Adjust filesystem access/modification times back in time
            age_days = file_ages.get(filename, 0.0)
            if age_days > 0.0:
                stale_time = time.time() - (age_days * 86400)
                os.utime(filepath, (stale_time, stale_time))
        print(f"[STARTUP] Created {len(sample_files)} sample files")
    
    # Start background services
    start_background_services(app)
    
    print(f"\n  Dashboard: http://localhost:5000")
    print(f"  Monitoring: {Config.DEFAULT_MONITOR_DIR}")
    print(f"  Press Ctrl+C to stop\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
