#!/usr/bin/env python3
"""
Face blurring using OpenCV DNN face detector + Haar cascade fallback
Optimized for detecting ALL faces including partially visible ones
"""

import cv2
import numpy as np
import os
import glob
from pathlib import Path


class HybridFaceDetector:
    """Hybrid face detector combining DNN and Haar cascades"""
    
    def __init__(self, dnn_confidence=0.15):
        """
        Initialize the hybrid face detector
        Lower confidence = more detections
        """
        # Get the models directory
        base_dir = Path(__file__).parent
        model_dir = base_dir / "models"
        
        # Load DNN model
        prototxt = model_dir / "deploy.prototxt.txt"
        caffemodel = model_dir / "res10_300x300_ssd_iter_140000.caffemodel"
        
        if prototxt.exists() and caffemodel.exists():
            self.dnn_net = cv2.dnn.readNetFromCaffe(str(prototxt), str(caffemodel))
            self.dnn_net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.dnn_net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            self.has_dnn = True
        else:
            self.has_dnn = False
            print("Warning: DNN model not found, using Haar cascades only")
        
        self.dnn_confidence = dnn_confidence
        
        # Load ALL available Haar cascades for maximum detection
        self.haar_cascades = []
        cascade_files = [
            'haarcascade_frontalface_default.xml',
            'haarcascade_frontalface_alt.xml',
            'haarcascade_frontalface_alt2.xml',
            'haarcascade_frontalface_alt_tree.xml',
            'haarcascade_profileface.xml',  # For side-view faces
            'haarcascade_eye.xml',  # Can help find eyes/faces
        ]
        
        for cascade_file in cascade_files:
            cascade = cv2.CascadeClassifier(cv2.data.haarcascades + cascade_file)
            if not cascade.empty():
                self.haar_cascades.append(cascade)
    
    def detect_dnn(self, image):
        """Detect faces using DNN with very low threshold"""
        if not self.has_dnn:
            return []
        
        h, w = image.shape[:2]
        blob = cv2.dnn.blobFromImage(
            cv2.resize(image, (300, 300)),
            1.0, (300, 300), (104.0, 177.0, 123.0)
        )
        self.dnn_net.setInput(blob)
        detections = self.dnn_net.forward()
        
        faces = []
        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > self.dnn_confidence:
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                x1, y1, x2, y2 = box.astype(int)
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                # Lower minimum size threshold
                if x2 - x1 > 15 and y2 - y1 > 15:
                    faces.append((x1, y1, x2 - x1, y2 - y1))
        return faces
    
    def detect_haar(self, image):
        """Detect faces using ALL Haar cascades with very aggressive settings"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        
        faces = []
        
        # More aggressive scale factors and lower minNeighbors
        for cascade in self.haar_cascades:
            # Very aggressive detection parameters
            for scale in [1.01, 1.05, 1.1, 1.15, 1.2, 1.3]:
                for minNeighbors in [1, 2, 3, 4, 5]:
                    try:
                        detected = cascade.detectMultiScale(gray, scale, minNeighbors)
                        for (x, y, w, h) in detected:
                            # Much lower minimum size threshold for partial faces
                            if w > 20 and h > 20:
                                # Check if it's not already detected (avoid duplicates)
                                is_duplicate = False
                                for (ox, oy, ow, oh) in faces:
                                    if abs(x - ox) < ow * 0.25 and abs(y - oy) < oh * 0.25:
                                        is_duplicate = True
                                        break
                                if not is_duplicate:
                                    faces.append((x, y, w, h))
                    except:
                        continue
        
        # Also try skin detection as last resort for partial faces
        ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
        lower = np.array([0, 135, 85], dtype=np.uint8)
        upper = np.array([255, 180, 135], dtype=np.uint8)
        mask = cv2.inRange(ycrcb, lower, upper)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.erode(mask, kernel, iterations=1)
        mask = cv2.dilate(mask, kernel, iterations=2)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 800:  # Lower threshold
                x, y, w, h = cv2.boundingRect(contour)
                # Check aspect ratio - allow more variation
                if 0.2 < w/h < 5 and w > 25 and h > 25:
                    # Check overlap with existing faces
                    is_new = True
                    for (ox, oy, ow, oh) in faces:
                        ox1, ox2 = max(x, ox), min(x+w, ox+ow)
                        oy1, oy2 = max(y, oy), min(y+h, oy+oh)
                        if ox2 > ox1 and oy2 > oy1:
                            overlap = (ox2 - ox1) * (oy2 - oy1)
                            if overlap > min(w*h, ow*oh) * 0.2:
                                is_new = False
                                break
                    if is_new:
                        faces.append((x, y, w, h))
        
        return faces
    
    def detect(self, image):
        """
        Detect faces using hybrid approach
        """
        all_faces = []
        
        # First try DNN (more accurate)
        dnn_faces = self.detect_dnn(image)
        all_faces.extend(dnn_faces)
        
        # Then try Haar cascades (as backup)
        haar_faces = self.detect_haar(image)
        
        # Add non-duplicate Haar detections
        for (x, y, w, h) in haar_faces:
            is_duplicate = False
            for (ox, oy, ow, oh) in all_faces:
                # Check overlap
                ox1, ox2 = max(x, ox), min(x+w, ox+ow)
                oy1, oy2 = max(y, oy), min(y+h, oy+oh)
                if ox2 > ox1 and oy2 > oy1:
                    overlap = (ox2 - ox1) * (oy2 - oy1)
                    if overlap > min(w*h, ow*oh) * 0.25:
                        is_duplicate = True
                        break
            if not is_duplicate:
                all_faces.append((x, y, w, h))
        
        return all_faces


def blur_region(image, x, y, w, h):
    """Apply VERY strong blur to a region"""
    if w <= 0 or h <= 0:
        return
    
    h_img, w_img = image.shape[:2]
    x = max(0, min(x, w_img - 1))
    y = max(0, min(y, h_img - 1))
    w = min(w, w_img - x)
    h = min(h, h_img - y)
    
    if w <= 0 or h <= 0:
        return
    
    face = image[y:y+h, x:x+w]
    if face.size == 0:
        return
    
    # EXTREMELY strong blur - multiple passes
    # First pass: heavy Gaussian blur
    k = max(35, min(w, h) // 3)
    if k % 2 == 0:
        k += 1
    k = min(k, face.shape[0] if face.shape[0] % 2 == 1 else face.shape[0] - 1)
    k = min(k, face.shape[1] if face.shape[1] % 2 == 1 else face.shape[1] - 1)
    k = max(3, k)
    
    blurred = cv2.GaussianBlur(face, (k, k), 0)
    
    # Second pass: additional blur for extra security
    k2 = max(15, k // 2)
    if k2 % 2 == 0:
        k2 += 1
    blurred = cv2.GaussianBlur(blurred, (k2, k2), 0)
    
    # Third pass: pixelation for extra anonymity
    pixel_size = max(8, min(w, h) // 10)
    small = cv2.resize(face, (pixel_size, pixel_size), interpolation=cv2.INTER_AREA)
    pixelated = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
    
    # Blend pixelation with blur
    alpha = 0.5
    final = cv2.addWeighted(blurred, alpha, pixelated, 1 - alpha, 0)
    
    image[y:y+h, x:x+w] = final


def process_image(path, output_path, detector):
    """Process a single image"""
    img = cv2.imread(str(path))
    if img is None:
        print(f"Cannot load: {path}")
        return False
    
    # Detect faces using hybrid approach
    faces = detector.detect(img)
    
    print(f"{Path(path).name}: {len(faces)} faces detected")
    
    # Blur each detected face
    for (x, y, w, h) in faces:
        blur_region(img, x, y, w, h)
    
    # Save the result
    cv2.imwrite(str(output_path), img)
    return True


def main():
    """Main function to process all images"""
    base = Path(__file__).parent
    inp = base / "img"
    out = base / "blurred_images_dnn"
    out.mkdir(exist_ok=True)
    
    # Find all image files
    files = []
    for ext in ['*.jpg', '*.jpeg', '*.png']:
        files.extend(inp.glob(ext))
        files.extend(inp.glob(ext.upper()))
    
    if not files:
        print(f"No images found in {inp}")
        return
    
    print(f"Processing {len(files)} images with hybrid face detector...\n")
    print("Using: DNN + ALL Haar cascades + skin detection\n")
    
    # Initialize the hybrid face detector with VERY low threshold
    detector = HybridFaceDetector(dnn_confidence=0.15)
    
    # Process each image
    for f in sorted(files):
        process_image(f, out / f"blurred_{f.name}", detector)
    
    print(f"\nDone! Output: {out}")


if __name__ == "__main__":
    main()
