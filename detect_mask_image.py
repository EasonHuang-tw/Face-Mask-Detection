# USAGE
# python detect_mask_image.py --image images/pic1.jpeg

# import the necessary packages
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.models import load_model
import numpy as np
import argparse
import cv2
import os
import rospy
from cv_bridge import CvBridge,CvBridgeError
from std_msgs.msg import Int16
from sensor_msgs.msg import Image
bridge = CvBridge()
def mask_image():
        # construct the argument parser and parse the arguments
        ap = argparse.ArgumentParser()
        ap.add_argument("-i", "--image",
                help="path to input image")
        ap.add_argument("-f", "--face", type=str,
                default="face_detector",
                help="path to face detector model directory")
        ap.add_argument("-m", "--model", type=str,
                default="mask_detector.model",
                help="path to trained face mask detector model")
        ap.add_argument("-c", "--confidence", type=float, default=0.5,
                help="minimum probability to filter weak detections")
        args = vars(ap.parse_args())

        # load our serialized face detector model from disk
        print("[INFO] loading face detector model...")
        prototxtPath = os.path.sep.join([args["face"], "deploy.prototxt"])
        weightsPath = os.path.sep.join([args["face"],
                "res10_300x300_ssd_iter_140000.caffemodel"])
        net = cv2.dnn.readNet(prototxtPath, weightsPath)

        # load the face mask detector model from disk
        print("[INFO] loading face mask detector model...")
        model = load_model(args["model"])

        #image_pub = rospy.Publisher("image_topic_2",Image)
        has_mask_pub = rospy.Publisher("has_mask",Int16)

        has_face = 0
        cap = cv2.VideoCapture(0)
        while(1):
            #image = cv2.imread(args["image"])
            #image = cv2.imread(image_name[x])
            #x=x+1
            #x%=(len(image_name))
            ret, image = cap.read()
            image_message = bridge.cv2_to_imgmsg(image, encoding="passthrough")
            orig = image.copy()
            (h, w) = image.shape[:2]

            # construct a blob from the image
            blob = cv2.dnn.blobFromImage(image, 1.0, (300, 300),
                    (104.0, 177.0, 123.0))

            # pass the blob through the network and obtain the face detections
            print("[INFO] computing face detections...")
            net.setInput(blob)
            detections = net.forward()
            has_mask=0
            # loop over the detections
	
            for i in range(0, detections.shape[2]):
                # extract the confidence (i.e., probability) associated with
                # the detection
                confidence = detections[0, 0, i, 2]

                # filter out weak detections by ensuring the confidence is
                # greater than the minimum confidence
                if confidence > args["confidence"]:
                    # compute the (x, y)-coordinates of the bounding box for
                    # the object
                    box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                    (startX, startY, endX, endY) = box.astype("int")

                    # ensure the bounding boxes fall within the dimensions of
                    # the frame
                    (startX, startY) = (max(0, startX), max(0, startY))
                    (endX, endY) = (min(w - 1, endX), min(h - 1, endY))

                    # extract the face ROI, convert it from BGR to RGB channel
                    # ordering, resize it to 224x224, and preprocess it
                    face = image[startY:endY, startX:endX]
                    if(face.any()):
                        face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
                        face = cv2.resize(face, (224, 224))
                        face = img_to_array(face)
                        face = preprocess_input(face)
                        face = np.expand_dims(face, axis=0)

                        # pass the face through the model to determine if the face
                        # has a mask or not
                        (mask, withoutMask) = model.predict(face)[0]

                        # determine the class label and color we'll use to draw
                        # the bounding box and text
                        label = "Mask" if mask > withoutMask else "No Mask"
                        if i == 0:
                            if not mask > withoutMask:
                                #image_pub.publish(image_message)
                                has_mask_pub.publish(0)
                            else:
                                has_mask_pub.publish(1)

                        color = (0, 255, 0) if label == "Mask" else (0, 0, 255)

                        # include the probability in the label
                        label = "{}: {:.2f}%, face_num[{}]".format(label, max(mask, withoutMask) * 100,i)

                        # display the label and bounding box rectangle on the output
                        # frame
                        cv2.putText(image, label, (startX, startY - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)
                        cv2.rectangle(image, (startX, startY), (endX, endY), color, 2)
                    else:
                        pass

                # show the output image
                cv2.imshow("Output", image)
            if cv2.waitKey(1) == ord('q'):
                break
        #cv2.waitKey(0)
	
if __name__ == "__main__":
        rospy.init_node('mask_face_detect', anonymous=True)
        mask_image()
