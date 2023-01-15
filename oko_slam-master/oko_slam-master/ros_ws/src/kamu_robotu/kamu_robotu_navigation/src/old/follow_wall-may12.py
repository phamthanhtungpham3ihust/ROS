#! /usr/bin/env python
# We are looking for the wall. If we find wall, we turn left to keep wall always
# right side of the robot

import rospy
import os
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from tf import transformations
from std_srvs.srv import *

import math
import numpy as np

## Global variables
active_ = True
pub_ = None #Since we are using publisher in the functions as well we need to
# make it global

linear_velocity_ = 0.03
angular_velocity_ = 0.20

regions_ = {
        'east': 0,
        'north': 0,
        'west': 0,
        'south': 0,
}

state_ = 0 #Start from find the wall state
state_dict_ = {
    0: 'find the wall',
    1: 'turn left',
    2: 'follow the wall',
    3: 'turn right',
}

def wall_follower_switch(req):
    global active_
    active_ = req.data
    res = SetBoolResponse()
    res.success = True
    res.message = 'Done!'
    return res


def callback_laser(msg):
    global regions_

    # Our laser publishes 128 point per rotation
    # Let's divide these 128 point to total_region_number different region
    # LIDAR rotates counter-clockwise
    # Let's start from the absolute right direction region and rotate cclockwise
    # By taking mean value in reach region, we want to find out which region
    # has the closest object/wall
    # To eliminate Inf measurement, we used mean function
    # Yet another alternative for eliminating ones smaller than 0.092 m = np.mean(filter(lambda k : k > 0.092, x))
    MAX_LIDAR_RANGE = 3 #in meter
    total_region_number = 6 #East, North, West, South
    msg.ranges = np.array(msg.ranges)
    msg.ranges[msg.ranges<0.093] = np.nan
#    east_array = msg.ranges[124:127] + msg.ranges[0:3]
    north_array1 = msg.ranges[121:127]
    north_array2 = msg.ranges[0:6]

#    north_east_west_west = np.nanmean(msg.ranges[119:120])
#    north_east_west = np.nanmean(msg.ranges[115:118])
    north_east = np.nanmean(msg.ranges[110:120])
#    north_east_east = np.nanmean(msg.ranges[106:109])
#    north_east_east_east = np.nanmean(msg.ranges[103:105])

 #   north_west_west_west = np.nanmean(msg.ranges[22:22])
#    north_west_west = np.nanmean(msg.ranges[19:22])
    north_west = np.nanmean(msg.ranges[7:18])
#    north_west_east = np.nanmean(msg.ranges[9:12])
#    north_west_east_east = np.nanmean(msg.ranges[7:8])


#    regions_ = {
#      'north': np.nanmean(msg.ranges[28:36]),
#      'west': np.nanmean(msg.ranges[60:68]),
#      'south': np.nanmean(msg.ranges[92:100]),
#      'east': np.nanmean(east_array),
#      'n-e': np.nanmean(msg.ranges[10:22]),
#      'n-w': np.nanmean(msg.ranges[42:54])
#     }
    regions_ = {
      'north': min(np.nanmin(north_array1),np.nanmin(north_array2)),
      'west': np.nanmean(msg.ranges[19:32]),
      'south': np.nanmean(msg.ranges[60:68]),
      'east':  np.nanmean(msg.ranges[96:109]),
      'n-w': np.nanmin(north_west), #(north_west_east_east, north_west_east, north_west, north_west_west, north_west_west_west),
      'n-e': np.nanmin(north_east) #(north_east_east_east, north_east_east, north_east, north_east_west, north_east_west_west),
     }

    take_action()

def change_state(state):
    global state_, state_dict_
    if state is not state_:
        print 'Wall follower - [%s] - %s' % (state, state_dict_[state])
        state_ = state

def take_action():
    global regions_, linear_velocity_, angular_velocity_
    regions = regions_
    msg = Twist()
    linear_x = 0
    angular_z = 0
    state_description = ''

    max_dist2robot = 0.25
    min_dist2robot = 0.092
    max_dist2obj = 0.25
    min_dist2obj = 0.092

    # If there exists an object only north then turn left --> Case 2
    # Positive turn around z axis corresponds to turning left

    if regions['north'] < max_dist2robot and regions['west'] > max_dist2robot and regions['east'] > max_dist2robot and regions['north'] > min_dist2robot:
            state_description = 'case 2 - north'
            change_state(3)
    elif regions['n-w'] < max_dist2obj and regions['n-e'] > max_dist2obj and regions['n-w'] > min_dist2obj:
        state_description = 'case 9 nw'
        change_state(3)
    elif regions['n-w'] > max_dist2obj and regions['n-e'] < max_dist2obj and regions['n-e'] > min_dist2obj :
        state_description = 'case 10 ne'
        change_state(1)
    elif regions['n-w'] < max_dist2obj and regions['n-e'] < max_dist2obj and regions['north'] > max_dist2robot and regions['n-w'] > min_dist2obj and regions['n-e'] > min_dist2obj:
        state_description = 'case 11 ne nw'
        change_state(0)
    elif regions['n-w'] < max_dist2obj and regions['n-e'] < max_dist2obj and regions['north'] < max_dist2robot and regions['n-w'] > min_dist2obj and regions['n-e'] > min_dist2obj:
        state_description = 'case 11 ne nw n'
        change_state(3)
    else:
        if regions['north'] > max_dist2robot and regions['west'] > max_dist2robot and regions['east'] > max_dist2robot:
            state_description = 'case 1 - nothing'
            change_state(0)
        elif regions['north'] < max_dist2robot and regions['west'] > max_dist2robot and regions['east'] > max_dist2robot and regions['north'] > min_dist2robot:
            state_description = 'case 2 - north'
            change_state(3)
        elif regions['north'] > max_dist2robot and regions['west'] > max_dist2robot and regions['east'] < max_dist2robot and regions['east'] > min_dist2robot:
            state_description = 'case 3 - east'
            change_state(2)
        elif regions['north'] > max_dist2robot and regions['west'] < max_dist2robot and regions['east'] > max_dist2robot and regions['west'] > min_dist2robot:
            state_description = 'case 4 - west'
            change_state(2)
        elif regions['north'] < max_dist2robot and regions['west'] > max_dist2robot and regions['east'] < max_dist2robot and regions['east'] > min_dist2robot and regions['north'] > min_dist2robot:
            state_description = 'case 5 - north and east'
            change_state(1)
        elif regions['north'] < max_dist2robot and regions['west'] < max_dist2robot and regions['east'] > max_dist2robot and regions['west'] > min_dist2robot and regions['north'] > min_dist2robot:
            state_description = 'case 6 - north and west'
            change_state(3)
        elif regions['north'] < max_dist2robot and regions['west'] < max_dist2robot and regions['east'] < max_dist2robot and regions['east'] > min_dist2robot and regions['west'] > min_dist2robot and regions['north'] > min_dist2robot:
            state_description = 'case 7 - north and west and east'
            change_state(3)
        elif regions['north'] > max_dist2robot and regions['west'] < max_dist2robot and regions['east'] < max_dist2robot and regions['east'] > min_dist2robot and regions['west'] > min_dist2robot:
            state_description = 'case 8 - west and east'
            change_state(0)
        else:
            state_description = 'Unknown Case GG WP!'
            rospy.loginfo(regions)

    rospy.loginfo(state_description)
    rospy.loginfo(regions)


def find_wall():
    msg = Twist()
    msg.linear.x = linear_velocity_
    msg.angular.z = 0
    return msg

def turn_left():
    msg = Twist()
    msg.angular.z = angular_velocity_
    msg.linear.x = 0
    return msg

def turn_right():
    msg = Twist()
    msg.angular.z = -angular_velocity_
    msg.linear.x = 0
    return msg

def follow_the_wall():
    global regions_

    msg = Twist()
    msg.linear.x = linear_velocity_
    msg.angular.z = 0
    return msg
def sd_hook():
    msg = Twist()
    msg.linear.x = 0
    msg.angular.z = 0
    pub_.publish(msg)

def main():
    global pub_, active_
    rospy.init_node('follow_wall')


    pub_ = rospy.Publisher('/cmd_vel', Twist, queue_size=1)

    sub = rospy.Subscriber('/scan', LaserScan, callback_laser)

    srv = rospy.Service('wall_follower_switch', SetBool, wall_follower_switch)

    rospy.on_shutdown(sd_hook)

    current_duration = rospy.get_time()
    print "current_duration = " + str(current_duration)
    d = rospy.Duration.from_sec(60.0*12)
    desired_duration = current_duration + d.to_sec()
    print "desired_duration = " + str(desired_duration)
    rate = rospy.Rate(5)
    while not rospy.is_shutdown():
        if not active_:
            rate.sleep()
            continue
        msg = Twist()
        if state_ == 0:
            msg = find_wall()
            #print "Find wall"
        elif state_ == 1:
            msg = turn_left()
            #print "Turn Left"
        elif state_ == 3:
            msg = turn_right()
            #print "Turn Right Bitch"
        elif state_ == 2:
            msg = follow_the_wall()
            #print "Follow the Wall Bitch"
            pass
        else:
            rospy.logerr('Unknown state! GG WP :(')
        pub_.publish(msg)
        if current_duration >= desired_duration:
            try:
                os.system("rosnode kill /oko_bag")
                rospy.signal_shutdown('Good bye')
            except Exception as e:
                pass
        current_duration = rospy.get_time()
        rate.sleep()
if __name__ == '__main__':
    main()
