from spike import PrimeHub, Motor, MotorPair
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
    for count, _ in enumerate(funktionen, start=1):
        x, y = divmod(count - 1, 5)
        light = 100 if count == index else 75
        hub.light_matrix.set_pixel(x, y, light)

def breakFunction(args):
    global cancel, activeMain
    if not activeMain:
        cancel = True

def read_battery():
    voltage = battery.voltage()
    status = "battery voltage is too low: " if voltage < 8000 else "battery voltage: "
    print(f"{status}{voltage}>>>> please charge robot <<<<" if voltage < 8000 else "")

def getDrivenDistance(data):
    left_degrees = abs(data.leftMotor.get_degrees_counted() - data.left_Startvalue)
    right_degrees = abs(data.rightMotor.get_degrees_counted() - data.right_Startvalue)
    print(f"{left_degrees} .:. {right_degrees}")
    return (left_degrees + right_degrees) / 2

def driveMotor(rotations, speed, port):
    global runSmall, run_generator, cancel
    if cancel:
        runSmall = run_generator = False
    while runSmall:
        smallMotor = Motor(port)
        smallMotor.set_degrees_counted(0)
        while abs(smallMotor.get_degrees_counted()) <= abs(rotations) * 360 and not cancel:
            smallMotor.start_at_power(speed)
            yield
        smallMotor.stop()
        runSmall = run_generator = False
    yield

def getGyroValue():
    global lastAngle, oldAngle, gyroValue
    angle = hub.motion_sensor.get_yaw_angle()
    if angle != lastAngle:
        oldAngle = lastAngle
    lastAngle = angle
    if angle in [179, -180] and oldAngle == angle - 1:
        hub2.motion.yaw_pitch_roll(0)
        gyroValue += 179 if angle == 179 else -180
    return gyroValue + angle

class DriveBase:
    def __init__(self, hub, leftMotor, rightMotor):
        self.hub = hub
        self.leftMotor = Motor(leftMotor)
        self.rightMotor = Motor(rightMotor)
        self.movement_motors = MotorPair(leftMotor, rightMotor)

    def drive(self, distance, speed, generator=None):
        global run_generator, runSmall, cancel
        if cancel:
            return
        if generator is None:
            run_generator = False
        self.left_Startvalue = self.leftMotor.get_degrees_counted()
        self.right_Startvalue = self.rightMotor.get_degrees_counted()
        rotateDistance = (distance / 17.6) * 360
        drivenDistance = getDrivenDistance(self)
        change, old_change, integral, steeringSum = 0, 0, 0, 0
        invert = -1 if speed > 0 else 1
        hub.motion_sensor.reset_yaw_angle()
        while drivenDistance < rotateDistance and not cancel:
            if run_generator:
                next(generator)
            oldDrivenDistance = drivenDistance
            drivenDistance = getDrivenDistance(self)
            change = getGyroValue()
            steering = max(-50, min(change + integral + steeringSum * 0.02 + (change - old_change), 50))
            print(f"steering: {steering} gyro: {change} integral: {integral}")
            steeringSum += change
            integral += change - old_change
            old_change = change
            self.movement_motors.start_at_power(int(speed), invert * int(steering))
        self.movement_motors.stop()
        run_generator = runSmall = True

    def turn(self, angle, speed):
        global cancel
        if cancel:
            return
        speed = abs(speed)
        steering = 1 if angle > 0 else -2
        angle *= 2400 / 2443
        target_angle = getGyroValue() + angle
        while abs(getGyroValue() - target_angle) > 1 and not cancel:
            current_angle = getGyroValue()
            angle_left = target_angle - current_angle
            current_speed = min(speed, abs(angle_left) + 5)
            self.movement_motors.start_tank_at_power(int(current_speed) * steering, -int(current_speed) * steering)
        self.movement_motors.stop()

db = DriveBase(hub, 'A', 'B')
funktionen = ['1', '2', '3', '4', '5', '6']
hub2.button.right.callback(breakFunction)

read_battery()
index = 1
write_display(funktionen, index)

while True:
    activeMain = True
    if hub.left_button.is_pressed():
        index = len(funktionen) if index == 1 else index - 1
        print(funktionen[index - 1])
        write_display(funktionen, index)
        time.sleep(0.15)
    if hub.right_button.is_pressed():
        index = 1 if index == len(funktionen) else index + 1
        print(funktionen[index - 1])
        write_display(funktionen, index)
        time.sleep(0.15)
    
read_battery()
sys.exit("ended program successfully")
