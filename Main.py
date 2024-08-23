# LEGO type:standard slot:0 autostart

from spike import PrimeHub, Button, StatusLight, ForceSensor, MotionSensor, Speaker, ColorSensor, App, DistanceSensor, Motor, MotorPair
from spike.control import wait_for_seconds, wait_until, Timer
from spike import LightMatrix
from hub import battery
import hub as hub2
import sys
import time


hub = PrimeHub()
lastAngle = 0
oldAngle = 0
gyroValue = 0
runSmall = True
run_generator = True 
cancel = False
activeMain = False


def write_display(funktionen, index):
    counting = 0
    x = -1
    y = 0
    for entry in funktionen:
        light = 75
        counting += 1
        if counting == index:
            light = 100
        if x == 4:
            y += 1
            x = 0
            hub.light_matrix.set_pixel(x, y, light)
        else:
            x += 1
            hub.light_matrix.set_pixel(x, y, light)

def breakFunction(args):

    global cancel, activeMain
    if not activeMain:
        cancel = True

def read_battery():
    
    if battery.voltage() < 8000: 
        print("battery voltage is too low: " + str(battery.voltage()) + ">>>> please charge robot <<<<")
    else:
        print("battery voltage: " + str(battery.voltage()))

    return 

def getDrivenDistance(data):

        print(str(abs(data.leftMotor.get_degrees_counted() - data.left_Startvalue)) + " .:. " + str(abs(data.rightMotor.get_degrees_counted() - data.right_Startvalue)))

        drivenDistance = (
                        abs(data.leftMotor.get_degrees_counted() - data.left_Startvalue) + 
                        abs(data.rightMotor.get_degrees_counted() - data.right_Startvalue)) / 2

        return drivenDistance

def driveMotor(rotations, speed, port):
           
    global runSmall
    global run_generator
    global cancel

    if cancel:
        runSmall = False
        run_generator = False


    while runSmall:
        smallMotor = Motor(port)
        smallMotor.set_degrees_counted(0)
        loop_small = True
        while loop_small:
            drivenDistance = smallMotor.get_degrees_counted()
            smallMotor.start_at_power(speed)
            if (abs(drivenDistance) > abs(rotations) * 360):
                loop_small = False
            if cancel:
                loop_small = False
            yield

        smallMotor.stop()
        runSmall = False
        run_generator = False
    yield

def getGyroValue():

    #this method is used to return the absolute gyro Angle and the angle returned by this method doesn't reset at 180 degree
    global lastAngle
    global oldAngle
    global gyroValue

    #gets the angle returned by the spike prime program. The problem is the default get_yaw_angle resets at 180 and -179 back to 0
    angle = hub.motion_sensor.get_yaw_angle()

    if angle != lastAngle:
        oldAngle = lastAngle
        
    lastAngle = angle

    if angle == 179 and oldAngle == 178:
        hub2.motion.yaw_pitch_roll(0)#reset
        gyroValue += 179
        angle = 0
    
    if angle == -180 and oldAngle == -179:
        hub2.motion.yaw_pitch_roll(0) #reset
        gyroValue -= 180   
        angle = 0

    return gyroValue + angle

class DriveBase:

    def __init__(self, hub, leftMotor, rightMotor):
        self.hub = hub
        self.leftMotor = Motor(leftMotor)
        self.rightMotor = Motor(rightMotor)
        self.movement_motors = MotorPair(leftMotor, rightMotor) 


    def drive(self, distance, speed, generator=None):
        
        if cancel:
            return

        global run_generator, runSmall
        if generator == None:
            run_generator = False

        self.left_Startvalue = self.leftMotor.get_degrees_counted()
        self.right_Startvalue = self.rightMotor.get_degrees_counted()
        rotateDistance = (distance / 17.6) * 360
        drivenDistance = getDrivenDistance(self)
        motors = self.movement_motors
        loop = True
        change = 0
        old_change = 0
        integral = 0
        steeringSum = 0
        invert = -1

        if speed < 0:
            invert = 1

        hub.motion_sensor.reset_yaw_angle()

        while loop:
            if cancel:
                break

            if run_generator:
                next(generator)

            oldDrivenDistance = drivenDistance
            drivenDistance = getDrivenDistance(self)
            change = getGyroValue()

            steering = change + integral + steeringSum * 0.02 + (change - old_change)
            steering = max(-50, min(steering, 50))
            print("steering: " + str(steering) + " gyro: " + str(change) + " integral: " + str(integral))

            steeringSum += change
            integral += change - old_change
            old_change = change

            motors.start_at_power(int(speed), invert * int(steering))
            if rotateDistance < drivenDistance:                   
                loop = False

        motors.stop()
        run_generator = True
        runSmall = True
        return

    def turn(self, angle, speed):

        global cancel

        if cancel:
            return

        speed = abs(speed)
        steering = 1 if angle > 0 else -2
        
        print(2400/2443)

        # Gyro sensor calibration
        angle = angle * (2400/2443)  # Experimental value based on 20 rotations of the robot

        gyro_start_value = getGyroValue()
        target_angle = gyro_start_value + angle 

        while abs(getGyroValue() - target_angle) > 1:  # 1 degree tolerance

            if cancel:
                break

            current_angle = getGyroValue()
            angle_left = target_angle - current_angle

            current_speed = min(speed, abs(angle_left) + 5)  # +5 to maintain minimum speed

            self.movement_motors.start_tank_at_power(int(current_speed) * steering, -int(current_speed) * steering)

        self.movement_motors.stop()

        return

db = DriveBase(hub, 'A', 'B')

funktionen = ['1', '2', '3', '4', '5', '6']

hub2.button.right.callback(breakFunction)

read_battery()

index = 1
write_display(funktionen, index)

while True:
    activeMain = True
    if hub.left_button.is_pressed():
        if index == 1:
            index = len(funktionen)
        else:
            index -= 1
        print(funktionen[index-1])
        write_display(funktionen, index)
        time.sleep(0.15)
    if hub.right_button.is_pressed():
        if index == len(funktionen):
            index = 1
        else:
            index += 1
        print(funktionen[index-1])
        write_display(funktionen, index)
        time.sleep(0.15)
    
read_battery()

sys.exit("ended program successfully")