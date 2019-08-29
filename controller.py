#!/usr/bin/env python2

# DD2410 Introduction to Robotics
# Assignment 1
#
# Arturs Kurzemnieks (artursk@kth.se)


import rospy
import actionlib
from irob_assignment_1.msg import GetNextGoalAction, GetNextGoalActionGoal, GetNextGoalActionResult
from irob_assignment_1.srv import GetSetpoint, GetSetpointRequest, GetSetpointResponse
from geometry_msgs.msg import Twist
from nav_msgs.msg import Path
import tf2_ros
import tf2_geometry_msgs
from math import atan2, hypot, fabs, copysign

# Use to transform between frames
tf_buffer = None
listener = None

# The exploration simple action client
goal_client = None
# The collision avoidance service client
control_client = None
# The velocity command publisher
pub = None

# The robots frame
robot_frame_id = "base_link"

# Max linear velocity (m/s)
max_linear_velocity = 0.5
# Max angular velocity (rad/s)
max_angular_velocity = 1.0

best_gain = 0
best_path = None
has_path = False

def on_goal_active():
    rospy.loginfo("Path goal sent, waiting for response...")

def on_goal_feedback(feedback):
    global best_gain, best_path, has_path
    if feedback.gain > best_gain:    # if newly received path is at least 2 times better, switch to that
        best_gain = feedback.gain
        best_path = feedback.path

    if not has_path:
        has_path = True
        move(best_path)

def on_goal_done(state, result):
    if state == actionlib.TerminalState.SUCCEEDED:
        print result
    else:
        rospy.loginfo("Something went wrong...")

def move(path):
    global control_client, robot_frame_id, pub, has_path
    rate = rospy.Rate(10)

    while path.poses:
        # Call service client with path
        res = control_client(path)
        # rospy.loginfo(res.setpoint.header.frame_id) # "map"

        new_path = res.new_path
        setpoint = res.setpoint

        transform = tf_buffer.lookup_transform(setpoint.header.frame_id, "base_link", rospy.Time(0))
        transformed_setpoint = tf2_geometry_msgs.do_transform_point(setpoint, transform)

        # Transform Setpoint from service client
        # transform = tf_buffer.
        # transformed_setpoint = tf2_geometry_msgs.do_transform_point(setpoint, transform)

        # Create Twist message from the transformed Setpoint

        twist_msg = Twist()

        linear_vel = 0.5 * hypot(transformed_setpoint.point.x, transformed_setpoint.point.x)
        if fabs(linear_vel) >= max_linear_velocity:
            linear_vel = copysign(max_linear_velocity, linear_vel)

        angular_vel = 4 * atan2(transformed_setpoint.point.y, transformed_setpoint.point.x)
        if fabs(angular_vel) >= max_angular_velocity:
            angular_vel = copysign(max_angular_velocity, angular_vel)
            linear_vel = 0

        twist_msg.linear.x = linear_vel
        twist_msg.angular.z = angular_vel

        # Publish Twist
        pub.publish(twist_msg)
        rate.sleep()
        
        path = new_path

    has_path = False
    # Call service client again if the returned path is not empty and do stuff again

    # Send 0 control Twist to stop robot

    # Get new path from action server


def get_path():
    global goal_client

    goal = GetNextGoalActionGoal()  # no arguments for the goal needed
    goal_client.send_goal(goal, active_cb=on_goal_active, feedback_cb=on_goal_feedback, done_cb=on_goal_done)


if __name__ == "__main__":

    # Init node
    rospy.init_node('burger_controller', anonymous=True)    # anonymous ensures unique node name for the instance

    # Init TF2 listener
    tf_buffer = tf2_ros.Buffer()
    listener = tf2_ros.TransformListener(tf_buffer)

    # Init publisher
    pub = rospy.Publisher('cmd_vel', Twist, queue_size=10)  # creates publisher for "cmd_vel" topic with Twist message type

    # Init simple action server
    goal_client = actionlib.SimpleActionClient('get_next_goal', GetNextGoalAction)
    goal_client.wait_for_server()
    
    # Init service client
    rospy.wait_for_service('get_setpoint')
    control_client = rospy.ServiceProxy('get_setpoint', GetSetpoint)

    # while not rospy.is_shutdown():
    #     get_path()

    # Call get path
    get_path()
    # Spin
    rospy.spin()