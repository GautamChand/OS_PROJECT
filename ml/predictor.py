"""
Smart Adaptive File Compression System — Access Predictor
Lightweight ML model to predict file access patterns.
Demonstrates OS Concept: Page Replacement Prediction (LRU/LFU).
"""
import os
import numpy as np
from datetime import datetime

from config import Config
from database import get_db_connection, db_execute
from ml.feature_extractor import FeatureExtractor


class AccessPredictor:
    """
    Predicts whether a file will be accessed soon.
    
    OS Concept: Page Replacement Algorithm
    - Similar to how OS predicts which memory pages will be needed
    - Uses historical access patterns to predict future access
    - Falls back to rule-based classification when insufficient data
    
    Uses RandomForestClassifier from scikit-learn when enough training data exists.
    """
    
    def __init__(self):
        self.model = None
        self.is_trained = False
        self.training_samples = 0
        self.feature_names = FeatureExtractor.get_feature_names()
    
    def _has_enough_data(self):
        """Check if there's enough access history to train."""
        count = db_execute(
            'SELECT COUNT(*) as cnt FROM access_history',
            fetch_one=True
        )
        return count and count['cnt'] >= Config.ML_MIN_TRAINING_RECORDS
    
    def train(self):
        """
        Train the prediction model on historical access data.
        
        Labels:
            1 = file was accessed within next 24 hours (after a given snapshot)
            0 = file was NOT accessed within next 24 hours
        """
        if not self._has_enough_data():
            print("[ML] Not enough training data. Using rule-based classification.")
            return False
        
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.model_selection import train_test_split
            import joblib
        except ImportError:
            print("[ML] scikit-learn not available. Using rule-based classification.")
            return False
        
        conn = get_db_connection()
        try:
            # Get all files with their metadata
            files = conn.execute('''
                SELECT f.*, 
                    (SELECT COUNT(*) FROM access_history ah 
                     WHERE ah.file_id = f.id 
                     AND julianday(ah.accessed_at) > julianday('now') - 1) as recent_access
                FROM files f
            ''').fetchall()
            
            if len(files) < 10:
                return False
            
            X = []
            y = []
            
            for file in files:
                file_dict = dict(file)
                
                # Get access history for this file
                history = conn.execute(
                    'SELECT * FROM access_history WHERE file_id = ? ORDER BY accessed_at',
                    (file_dict['id'],)
                ).fetchall()
                history = [dict(h) for h in history]
                
                features = FeatureExtractor.extract(file_dict, history)
                X.append(features)
                
                # Label: was the file accessed recently?
                y.append(1 if file_dict['recent_access'] > 0 else 0)
            
            X = np.array(X)
            y = np.array(y)
            
            # Train/test split
            if len(set(y)) < 2:
                # Not enough variety in labels
                print("[ML] Not enough label variety. Using rule-based classification.")
                return False
            
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Train RandomForest
            self.model = RandomForestClassifier(
                n_estimators=50,
                max_depth=5,
                random_state=42,
                n_jobs=-1,
            )
            self.model.fit(X_train, y_train)
            
            # Evaluate
            accuracy = self.model.score(X_test, y_test)
            self.is_trained = True
            self.training_samples = len(X)
            
            # Save model
            os.makedirs(os.path.dirname(Config.ML_MODEL_PATH), exist_ok=True)
            joblib.dump(self.model, Config.ML_MODEL_PATH)
            
            print(f"[ML] Model trained. Accuracy: {accuracy:.2%} ({len(X)} samples)")
            
            return True
            
        finally:
            conn.close()
    
    def load_model(self):
        """Load a previously trained model."""
        try:
            import joblib
            if os.path.exists(Config.ML_MODEL_PATH):
                self.model = joblib.load(Config.ML_MODEL_PATH)
                self.is_trained = True
                return True
        except Exception:
            pass
        return False
    
    def predict(self, file_metadata, access_history=None):
        """
        Predict probability of file being accessed soon.
        
        Returns:
            dict with prediction, probability, and method used
        """
        features = FeatureExtractor.extract(file_metadata, access_history)
        
        if self.is_trained and self.model is not None:
            try:
                X = np.array([features])
                prob = self.model.predict_proba(X)[0]
                
                # prob[1] = probability of being accessed soon
                access_probability = prob[1] if len(prob) > 1 else prob[0]
                
                return {
                    'will_access_soon': access_probability >= Config.ML_PREDICTION_THRESHOLD,
                    'probability': round(float(access_probability), 4),
                    'confidence': round(float(max(prob)), 4),
                    'method': 'ml_model',
                    'features': dict(zip(self.feature_names, features)),
                }
            except Exception:
                pass
        
        # Fall back to rule-based prediction
        return self._rule_based_predict(file_metadata, features)
    
    def _rule_based_predict(self, file_metadata, features):
        """Rule-based prediction fallback."""
        access_count = features[0]
        days_since_access = features[1]
        
        # Simple heuristic based on access frequency and recency
        if access_count >= 10 and days_since_access < 1:
            probability = 0.9
        elif access_count >= 5 and days_since_access < 3:
            probability = 0.7
        elif access_count >= 2 and days_since_access < 7:
            probability = 0.5
        elif access_count >= 1 and days_since_access < 14:
            probability = 0.3
        else:
            probability = 0.1
        
        return {
            'will_access_soon': probability >= Config.ML_PREDICTION_THRESHOLD,
            'probability': probability,
            'confidence': 0.5,  # lower confidence for rule-based
            'method': 'rule_based',
            'features': dict(zip(self.feature_names, features)),
        }
    
    def predict_batch(self, files_metadata):
        """Predict for multiple files."""
        results = []
        for file_meta in files_metadata:
            prediction = self.predict(file_meta)
            prediction['file_id'] = file_meta.get('id')
            prediction['filename'] = file_meta.get('filename')
            results.append(prediction)
        return results
    
    def get_feature_importance(self):
        """Get feature importance from the trained model."""
        if self.is_trained and self.model is not None:
            try:
                importances = self.model.feature_importances_
                return dict(zip(self.feature_names, [round(float(x), 4) for x in importances]))
            except Exception:
                pass
        return None
    
    def get_status(self):
        """Get model status information."""
        return {
            'is_trained': self.is_trained,
            'method': 'ml_model' if self.is_trained else 'rule_based',
            'training_samples': self.training_samples,
            'model_path': Config.ML_MODEL_PATH if self.is_trained else None,
            'feature_importance': self.get_feature_importance(),
        }


# Global predictor instance
access_predictor = AccessPredictor()
