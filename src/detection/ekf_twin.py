"""
AEGIS Digital Twin — Kinematic Extended Kalman Filter (EKF)
Author: Team Persistent Formation
Inspired by robust Guidance, Navigation, and Control (GNC) principles.

This module maintains a physics-based Digital Twin of the UAV.
By computing the Mahalanobis distance of the measurement innovation (residual),
we detect sensor spoofing (e.g., NavIC/GPS) and physical deviations mathematically.
"""
import numpy as np
from typing import Optional, Tuple
from ..simulator.mavlink_simulator import MAVLinkPacket, MSG_GPS_RAW_INT, MSG_GLOBAL_POSITION_INT

class EKFCyberTwin:
    """
    Extended Kalman Filter tracking 6-DOF kinematics.
    State X: [x, y, z, vx, vy, vz]^T
    """
    def __init__(self, dt: float = 0.1):
        self.dt = dt
        self.state_dim = 6
        self.meas_dim = 3
        
        # State vector
        self.x = np.zeros((self.state_dim, 1))
        
        # Covariance matrix
        self.P = np.eye(self.state_dim) * 10.0
        
        # State transition matrix (Constant Velocity Model)
        self.F = np.eye(self.state_dim)
        for i in range(3):
            self.F[i, i+3] = dt
            
        # Process noise covariance (Q)
        q = 0.1
        self.Q = np.eye(self.state_dim) * q
        
        # Measurement matrix (observing x, y, z positions)
        self.H = np.zeros((self.meas_dim, self.state_dim))
        for i in range(3):
            self.H[i, i] = 1.0
            
        # Measurement noise covariance (R) - represents normal NavIC/GPS noise
        self.R = np.eye(self.meas_dim) * 2.5
        
        self.initialized = False
        self.last_ts = 0.0

        # Geographical reference (for converting lat/lon to local cartesian)
        self.ref_lat = 0.0
        self.ref_lon = 0.0
        
        # Anomaly threshold (Mahalanobis distance squared, chi-square distribution)
        # 3 degrees of freedom, 99.9% confidence = 16.27
        self.chi2_threshold = 16.27

    def _latlon_to_xy(self, lat_e7: int, lon_e7: int) -> Tuple[float, float]:
        if not self.initialized:
            self.ref_lat = lat_e7 / 1e7
            self.ref_lon = lon_e7 / 1e7
            return 0.0, 0.0
            
        lat = lat_e7 / 1e7
        lon = lon_e7 / 1e7
        
        dx = (lon - self.ref_lon) * 111000.0 * np.cos(np.radians(self.ref_lat))
        dy = (lat - self.ref_lat) * 111000.0
        return dx, dy

    def predict(self, dt: float):
        """Predict the next state of the Digital Twin."""
        # Update F for dynamic dt
        for i in range(3):
            self.F[i, i+3] = dt
            
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q

    def update(self, z: np.ndarray) -> float:
        """
        Update with sensor measurement and calculate Mahalanobis distance of innovation.
        Returns the Mahalanobis distance squared (anomaly score).
        """
        # Innovation (residual)
        y = z - (self.H @ self.x)
        
        # Innovation covariance
        S = self.H @ self.P @ self.H.T + self.R
        S_inv = np.linalg.inv(S)
        
        # Mahalanobis distance squared
        mahalanobis_sq = float(y.T @ S_inv @ y)
        
        # Kalman Gain
        K = self.P @ self.H.T @ S_inv
        
        # Update state and covariance
        self.x = self.x + K @ y
        I = np.eye(self.state_dim)
        self.P = (I - K @ self.H) @ self.P
        
        return mahalanobis_sq

    def process_packet(self, pkt: MAVLinkPacket) -> Optional[dict]:
        """Process packet, run EKF, return alert if innovation is statistically improbable."""
        if pkt.msg_id not in (MSG_GPS_RAW_INT, MSG_GLOBAL_POSITION_INT):
            return None
            
        t = pkt.timestamp_s
        lat_e7 = pkt.payload.get('lat', 0)
        lon_e7 = pkt.payload.get('lon', 0)
        alt_m  = pkt.payload.get('alt', 0) / 1000.0

        dx, dy = self._latlon_to_xy(lat_e7, lon_e7)
        z = np.array([[dx], [dy], [alt_m]])
        
        if not self.initialized:
            self.x[0,0] = dx
            self.x[1,0] = dy
            self.x[2,0] = alt_m
            self.last_ts = t
            self.initialized = True
            return None
            
        dt = t - self.last_ts
        if dt <= 0: return None
        self.last_ts = t
        
        self.predict(dt)
        score = self.update(z)
        
        # If the sensor reading severely deviates from physics-based prediction:
        if score > self.chi2_threshold:
            return {
                'rule':        'EKF_DIGITAL_TWIN_ANOMALY',
                'severity':    'CRITICAL',
                'timestamp_s': t,
                'msg_id':      pkt.msg_id,
                'system_id':   pkt.system_id,
                'detail':      f"Kinematic EKF innovation Mahalanobis distance {score:.1f} > {self.chi2_threshold}. NavIC/GPS spoofing highly probable.",
                'sha256':      pkt.sha256(),
                'ml_score':    score,
            }
        return None
