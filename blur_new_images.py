#!/usr/bin/env python3
"""
Face blurring script - only blurs new images that haven't been processed yet.
Uses OpenCV DNN face detector + Haar cascade fallback.
"""

import cv2
import numpy as np
import os
from pathlib import Path


class HybridFaceDetector:
    """Hybrid face detector combining DNN and Haar cascades"""
    
    def __init__(self, dnn_confidence=0.15):
        base_dir = Path(__file__).parent
        model_dir = base_dir / "models"
        
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
        
        self.haar_cascades = []
        cascade_files = [
            'haarcascade_frontalface_default.xml',
            'haarcascade_frontalface_alt.xml',
            'haarcascade_frontalface_alt2.xml',
            'haarcascade_frontalface_alt_tree.xml',
            'haarcascade_profileface.xml',
            'haarcascade_eye.xml',
        ]
        
        for cascade_file in cascade_files:
            cascade = cv2.CascadeClassifier(cv2.data.haarcascades + cascade_file)
            if not cascade.empty():
                self.haar_cascades.append(cascade)
    
    def detect_dnn(self, image):
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
                if x2 - x1 > 15 and y2 - y1 > 15:
                    faces.append((x1, y1, x2 - x1, y2 - y1))
        return faces
    
    def detect_haar(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        
        faces = []
        
        for cascade in self.haar_cascades:
            for scale in [1.01, 1.05, 1.1, 1.15, 1.2, 1.3]:
                for minNeighbors in [1, 2, 3, 4, 5]:
                    try:
                        detected = cascade.detectMultiScale(gray, scale, minNeighbors)
                        for (x, y, w, h) in detected:
                            if w > 20 and h > 20:
                                is_duplicate = False
                                for (ox, oy, ow, oh) in faces:
                                    if abs(x - ox) < ow * 0.25 and abs(y - oy) < oh * 0.25:
                                        is_duplicate = True
                                        break
                                if not is_duplicate:
                                    faces.append((x, y, w, h))
                    except:
                        continue
        
        # Skin detection
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
            if area > 800:
                x, y, w, h = cv2.boundingRect(contour)
                if 0.2 < w/h < 5 and w > 25 and h > 25:
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
        all_faces = []
        
        dnn_faces = self.detect_dnn(image)
        all_faces.extend(dnn_faces)
        
        haar_faces = self.detect_haar(image)
        
        for (x, y, w, h) in haar_faces:
            is_duplicate = False
            for (ox, oy, ow, oh) in all_faces:
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
    
    k = max(35, min(w, h) // 3)
    if k % 2 == 0:
        k += 1
    k = min(k, face.shape[0] if face.shape[0] % 2 == 1 else face.shape[0] - 1)
    k = min(k, face.shape[1] if face.shape[1] % 2 == 1 else face.shape[1] - 1)
    k = max(3, k)
    
    blurred = cv2.GaussianBlur(face, (k, k), 0)
    
    k2 = max(15, k // 2)
    if k2 % 2 == 0:
        k2 += 1
    blurred = cv2.GaussianBlur(blurred, (k2, k2), 0)
    
    pixel_size = max(8, min(w, h) // 10)
    small = cv2.resize(face, (pixel_size, pixel_size), interpolation=cv2.INTER_AREA)
    pixelated = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
    
    alpha = 0.5
    final = cv2.addWeighted(blurred, alpha, pixelated, 1 - alpha, 0)
    
    image[y:y+h, x:x+w] = final


def load_blurred_list():
    """Load list of already blurred images"""
    base_dir = Path(__file__).parent
    tracker_file = base_dir / "img" / "blurred_images.txt"
    
    blurred = set()
    if tracker_file.exists():
        with open(tracker_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    try:
                        blurred.add(int(line))
                    except:
                        pass
    return blurred


def save_blurred_list(blurred):
    """Save list of blurred images"""
    base_dir = Path(__file__).parent
    tracker_file = base_dir / "img" / "blurred_images.txt"
    
    with open(tracker_file, 'w') as f:
        f.write("# This file tracks which images have been blurred\n")
        f.write("# Add image numbers here that have been processed\n\n")
        for num in sorted(blurred):
            f.write(f"{num}\n")


def main():
    base = Path(__file__).parent
    img_dir = base / "img"
    tracker_file = base_dir / "img" / "blurred_images.txt"
    
    # Load already blurred images
    blurred_images = load_blurred_list()
    print(f"Already blurred: {sorted(blurred_images)}")
    
    # Find all jpeg images in img folder
    new_images = []
    for i in range(1, 1000):  # Check up to 1000 images
        img_path = img_dir / f"{i}.jpeg"
        if img_path.exists() and i not in blurred_images:
            new_images.append(i)
    
    if not new_images:
        print("\nNo new images to blur!")
        return
    
    print(f"\nNew images to blur: {new_images}")
    
    # Initialize detector
    detector = HybridFaceDetector(dnn_confidence=0.15)
    
    # Process new images
    for img_num in new_images:
        img_path = img_dir / f"{img_num}.jpeg"
        print(f"\nProcessing {img_path.name}...")
        
        img = cv2.imread(str(img_path))
        if img is None:
            print(f"  Cannot load image")
            continue
        
        faces = detector.detect(img)
        print(f"  {len(faces)} faces detected")
        
        for (x, y, w, h) in faces:
            blur_region(img, x, y, w, h)
        
        # Save over original
        cv2.imwrite(str(img_path), img)
        print(f"  Saved")
        
        # Add to blurred list
        blurred_images.add(img_num)
    
    # Update tracker file
    save_blurred_list(blurred_images)
    
    print(f"\nDone! {len(new_images)} images blurred and saved.")


if __name__ == "__main__":
    main()
