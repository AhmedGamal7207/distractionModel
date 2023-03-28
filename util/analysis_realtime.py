# imports
import cv2
import numpy as np
import dlib
from math import hypot
from keras.models import load_model

class analysis:
    # Global values
    # values for eye positions
    eye_points = [36, 37, 38, 39, 40, 41]
    # dictionary for emotions
    emotions_dictionary = {0: 'Angry', 1: 'Fear', 2: 'Happy', 3: 'Sad', 4: 'Surprised', 5: 'Neutral'}
    emotions_weights = {0: 0.25, 1: 0.3, 2: 0.6, 3: 0.3, 4: 0.6, 5: 0.9}
    
    def __init__(self, frame_width, frame_height):
        self.emotion_model = load_model('./util/model/emotion_recognition.h5')
        self.detector = dlib.get_frontal_face_detector()
        self.predictor = dlib.shape_predictor(
            "./util/model/shape_predictor_68_face_landmarks.dat")
        self.faceCascade = cv2.CascadeClassifier(
            './util/model/haarcascade_frontalface_default.xml')
        #self.x = 0 # lr_gaze_ratio --> get_gaze_ratio()
        #self.y = 0 # ud_gaze_ratio --> get_gaze_ratio()
        self.emotion = 5
        # self.eye_ratio = 0 # ratio --> get_blinking_ratio()
        self.frame_count = 0
        self.cis = []
        self.frame_width = frame_width
        self.frame_height = frame_height

    def get_midpoint(self, p1, p2):
        return int((p1.x + p2.x) / 2), int((p1.y + p2.y) / 2)

    def detect_face(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detector(gray)
        
        # landmarks is considered a local variable
        # UnboundLocalError: cannot access local variable 'landmarks' where it is not associated with a value
        # TODO
        
        for face in faces:
            landmarks = self.predictor(gray, face)
            
            ci = self.display_messages()
            ci_to_color = {
                "You are highly focused!": (102, 255, 102),
                "You are focused.": (255, 128, 0),
                "Distracted!": (102, 178, 255),
                "Pay attention!": (0, 0, 255)
            }
            cv2.putText(
                frame, ci,
                # (50, 250), font, 2, (0, 0, 255), 3,
                (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, ci_to_color.get(ci, (0, 0, 0)), 3
            )
        return landmarks

    # Function for eye size
    def get_blinking_ratio(self, facial_landmarks):
        left_point = (facial_landmarks.part(
            self.eye_points[0]).x, facial_landmarks.part(self.eye_points[0]).y)
        right_point = (facial_landmarks.part(
            self.eye_points[3]).x, facial_landmarks.part(self.eye_points[3]).y)
        center_top = self.midpoint(facial_landmarks.part(
            self.eye_points[1]), facial_landmarks.part(self.eye_points[2]))
        center_bottom = self.midpoint(facial_landmarks.part(
            self.eye_points[5]), facial_landmarks.part(self.eye_points[4]))
        
        hor_line_lenght = hypot(
            (left_point[0] - right_point[0]), (left_point[1] - right_point[1]))
        ver_line_lenght = hypot(
            (center_top[0] - center_bottom[0]), (center_top[1] - center_bottom[1]))
        eye_ratio = ver_line_lenght / hor_line_lenght
        # We can use ratio to define object? variable eye_ratio and maybe no need to return it Idk
        # self.eye_ratio = ratio
        return eye_ratio
    
     # Gaze detection function
    def get_gaze_ratio(self, facial_landmarks, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) 
        left_eye_region = np.array([(facial_landmarks.part(self.eye_points[0]).x, facial_landmarks.part(self.eye_points[0]).y),
                                    (facial_landmarks.part(
                                        self.eye_points[1]).x, facial_landmarks.part(self.eye_points[1]).y),
                                    (facial_landmarks.part(
                                        self.eye_points[2]).x, facial_landmarks.part(self.eye_points[2]).y),
                                    (facial_landmarks.part(self.eye_points[3]).x,
                                     facial_landmarks.part(self.eye_points[3]).y),
                                    (facial_landmarks.part(self.eye_points[4]).x,
                                     facial_landmarks.part(self.eye_points[4]).y),
                                    (facial_landmarks.part(self.eye_points[5]).x, facial_landmarks.part(self.eye_points[5]).y)],
                                   np.int32)

        height, width = self.frame_height, self.frame_width
        mask = np.zeros((height, width), np.uint8)
        cv2.polylines(mask, [left_eye_region], True, 255, 2)
        cv2.fillPoly(mask, [left_eye_region], 255)
        eye = cv2.bitwise_and(gray, gray, mask=mask)

        min_x = np.min(left_eye_region[:, 0])
        max_x = np.max(left_eye_region[:, 0])
        min_y = np.min(left_eye_region[:, 1])
        max_y = np.max(left_eye_region[:, 1])
        gray_eye = eye[min_y: max_y, min_x: max_x]
        _, threshold_eye = cv2.threshold(gray_eye, 70, 255, cv2.THRESH_BINARY)

        height, width = threshold_eye.shape
        
        # Calculations for Left & Right gaze ratios
        left_side_threshold = threshold_eye[0: height, 0: int(width / 2)]
        left_side_white = cv2.countNonZero(left_side_threshold)
        right_side_threshold = threshold_eye[0: height, int(width / 2): width]
        right_side_white = cv2.countNonZero(right_side_threshold)

        # Calculations for Up & Down gaze ratios
        up_side_threshold = threshold_eye[0: int(height / 2), 0: int(width / 2)]
        up_side_white = cv2.countNonZero(up_side_threshold)
        down_side_threshold = threshold_eye[int(height / 2): height, 0: width]
        down_side_white = cv2.countNonZero(down_side_threshold)
        
        lr_gaze_ratio = (left_side_white + 10) / (right_side_white + 10)
        ud_gaze_ratio = (up_side_white + 10) / (down_side_white + 10)
        
        # self.x = lr_gaze_ratio
        # self.y = ud_gaze_ratio
        
        
        return lr_gaze_ratio, ud_gaze_ratio
    
    
    # Calculate weights for gaze
    # ud_gaze_ratio is unused in calculations
    def gaze_weights(self, eye_ratio, lr_gaze_ratio, ud_gaze_ratio):
        gaze_weights = 0

        if eye_ratio < 0.2:
            gaze_weights = 0
        elif eye_ratio > 0.2 and eye_ratio < 0.3:
            gaze_weights = 1.5
        else:
            if lr_gaze_ratio < 2 and lr_gaze_ratio > 1:
                gaze_weights = 5
            else:
                gaze_weights = 2
    
        return gaze_weights
    
    # Helper function for detect_emotion [1/4]
    def cascade_helper(self, gray):
        return self.faceCascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=7,
            minSize=(100, 100)
        )
    
    # Helper function for detect_emotion [2/4] 
    def crop_face(self, gray, face):
        x, y, width, height = face
        return gray[y:y + height, x:x + width]

    # Helper function for detect_emotion [3/4] 
    def preprocess_image(self, image):
        image = cv2.resize(image, (48, 48))
        image = image.reshape([-1, 48, 48, 1])
        image = np.multiply(image, 1.0 / 255.0)
        return image

    # Helper function for detect_emotion [4/4] 
    def get_emotion_probabilities(self, image):
        if self.frame_count % 5 != 0:
            return self.last_probab
        probab = self.emotion_model.predict(image)[0] * 100
        self.last_probab = probab
        return probab
    
    # Function for detecting emotion
    def detect_emotion(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.cascade_helper(gray)
        if not faces:
            return

        cropped_face = self.crop_face(gray, faces[0])
        test_image = self.preprocess_image(cropped_face)

        probab = self.get_emotion_probabilities(test_image)
        emotion = np.argmax(probab)
        self.emotion = emotion
        
        return emotion


    # What do we return here? 
    # TODO
    
    def display_messages(self):
        ci = self.gen_concentration_index()
        self.cis.append(ci)
        ci = self.process_ci()
        
        return ci

    # Seperate Gaze function from generate ci
    # TODO
    def gen_concentration_index(self, gaze_weights, emotion):
        
        gaze_weights = gaze_weights(self.eye_ratio) 

        # Concentration index is a percentage : max weights product = 4.5
        concentration_index = (self.emotions_weights[emotion] * gaze_weights) / 4.5
        
        if concentration_index > 0.65:
            return "You are highly focused!"
        elif concentration_index > 0.25 and concentration_index <= 0.65:
            return "You are focused."
        else:
            return "Pay attention!"


    def process_ci(self):
        if len(self.cis) > 40:
            if self.cis[-40:] == ["Pay attention!"] * 40:
                return "Pay attention!"
            elif self.cis[-20:] == ["Pay attention!"] * 20:
                return "Distracted!"
            else:
                for ci in self.cis[::-1]:
                    if ci != "Pay attention!":
                        return ci

    
    
    def tester (self):
        return "hi"