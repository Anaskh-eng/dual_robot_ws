// =============================================================================
// mission_controller.cpp
// Description : C++ ROS2 node that coordinates dual-robot navigation.
//               Each robot receives goals via the nav2_msgs/NavigateToPose
//               action, scoped under /TB3_1 and /TB3_2 namespaces.
//
// Architecture note:
//   - Action server topics are automatically resolved as:
//       /TB3_1/navigate_to_pose
//       /TB3_2/navigate_to_pose
//     because Nav2 bringup was launched under PushRosNamespace.
//   - Goals are sent concurrently; completion callbacks track each robot
//     independently.
// =============================================================================

#include "dual_robot_nav/mission_controller.hpp"

#include <cmath>
#include <chrono>
#include <memory>
#include <string>

#include "geometry_msgs/msg/quaternion.hpp"
#include "tf2/LinearMath/Quaternion.h"
#include "tf2_geometry_msgs/tf2_geometry_msgs.hpp"

using namespace std::chrono_literals;

namespace dual_robot_nav
{

// ── Helper: Convert yaw angle (radians) to ROS quaternion ─────────────────────
static geometry_msgs::msg::Quaternion yawToQuaternion(double yaw_rad)
{
  tf2::Quaternion q;
  q.setRPY(0.0, 0.0, yaw_rad);
  return tf2::toMsg(q);
}

// ── Constructor ───────────────────────────────────────────────────────────────
MissionController::MissionController(const rclcpp::NodeOptions & options)
: Node("mission_controller", options)
{
  RCLCPP_INFO(get_logger(), "MissionController initializing...");
  initClients();

  // Delay demo mission until action servers are confirmed available.
  // In production, replace this with a trigger from your warehouse WMS.
  startup_timer_ = create_wall_timer(
    3s,
    [this]() {
      startup_timer_->cancel();  // One-shot
      executeDemoMission();
    });
}

// ── Create action clients for both robots ─────────────────────────────────────
void MissionController::initClients()
{
  // Action topic = /<namespace>/navigate_to_pose  (resolved by Nav2 bringup)
  client_tb3_1_ = rclcpp_action::create_client<NavigateToPose>(
    this, "/TB3_1/navigate_to_pose");

  client_tb3_2_ = rclcpp_action::create_client<NavigateToPose>(
    this, "/TB3_2/navigate_to_pose");

  RCLCPP_INFO(get_logger(), "Action clients created for /TB3_1 and /TB3_2.");
}

// ── Demo mission: send one goal to each robot concurrently ────────────────────
void MissionController::executeDemoMission()
{
  // ── Define waypoints (adjust coordinates to match your warehouse layout) ──
  // Loading Docks
  const Waypoint loading_dock_TB3_1  = {"Loading Dock TB3_1",    -0.5,  -3.2, 1.57};
  const Waypoint loading_dock_TB3_2  = {"Loading Dock TB3_2",     0.5,  -3.2, 1.57};
  
  // Machines for TB3_1
  const Waypoint machine_M1 = {"Machine M1", -1.0, -1.2, 0.0};
  const Waypoint machine_M2 = {"Machine M2",  -3.2, 0.5, 0.0};
  
  // Machines for TB3_2
  const Waypoint machine_M3 = {"Machine M3",  3.2, 0.5, 0.0};
  const Waypoint machine_M4 = {"Machine M4",  1.0, -1.2, 0.0};

  RCLCPP_INFO(get_logger(), "Dispatching demo mission to both robots...");

  // TB3_1 → Loading Dock → M1 → M2
  sendGoal("TB3_1", loading_dock_TB3_1,
    [this, machine_M1, machine_M2, loading_dock_TB3_1](bool success, const std::string & robot_id) {
      if (success) {
        RCLCPP_INFO(get_logger(), "[%s] Reached Loading Dock. Ready for pickup.",
                    robot_id.c_str());
        // Next: TB3_1 goes to M1
        sendGoal("TB3_1", machine_M1,
          [this, machine_M2, loading_dock_TB3_1](bool m1_success, const std::string & id) {
            if (m1_success) {
              RCLCPP_INFO(get_logger(), "[%s] Reached Machine M1. Processing...",
                          id.c_str());
              // Next: TB3_1 goes to M2
              sendGoal("TB3_1", machine_M2,
                [this, loading_dock_TB3_1](bool m2_success, const std::string & id2) {
                  if (m2_success) {
                    RCLCPP_INFO(get_logger(), "[%s] Reached Machine M2. Mission complete.",
                                id2.c_str());
                    RCLCPP_INFO(get_logger(), "[%s] Returning to Loading Dock.", id2.c_str());
                    sendGoal("TB3_1", loading_dock_TB3_1,
                      [this](bool return_success, const std::string & id3) {
                        if (return_success) {
                          RCLCPP_INFO(get_logger(), "[%s] Returned to Loading Dock.", id3.c_str());
                        } else {
                          RCLCPP_WARN(get_logger(), "[%s] Failed to return to Loading Dock.", id3.c_str());
                        }
                      });
                  } else {
                    RCLCPP_WARN(get_logger(), "[%s] Failed to reach Machine M2.", id2.c_str());
                  }
                });
            } else {
              RCLCPP_WARN(get_logger(), "[%s] Failed to reach Machine M1.", id.c_str());
            }
          });
      } else {
        RCLCPP_WARN(get_logger(), "[%s] Failed to reach Loading Dock.", robot_id.c_str());
      }
    });

  // TB3_2 → Loading Dock → M3 → M4 (concurrent with TB3_1)
  sendGoal("TB3_2", loading_dock_TB3_2,
    [this, machine_M3, machine_M4, loading_dock_TB3_2](bool success, const std::string & robot_id) {
      if (success) {
        RCLCPP_INFO(get_logger(), "[%s] Reached Loading Dock. Ready for pickup.",
                    robot_id.c_str());
        // Next: TB3_2 goes to M3
        sendGoal("TB3_2", machine_M3,
          [this, machine_M4, loading_dock_TB3_2](bool m3_success, const std::string & id) {
            if (m3_success) {
              RCLCPP_INFO(get_logger(), "[%s] Reached Machine M3. Processing...",
                          id.c_str());
              // Next: TB3_2 goes to M4
              sendGoal("TB3_2", machine_M4,
                [this, loading_dock_TB3_2](bool m4_success, const std::string & id2) {
                  if (m4_success) {
                    RCLCPP_INFO(get_logger(), "[%s] Reached Machine M4. Mission complete.",
                                id2.c_str());
                    RCLCPP_INFO(get_logger(), "[%s] Returning to Loading Dock.", id2.c_str());
                    sendGoal("TB3_2", loading_dock_TB3_2,
                      [this](bool return_success, const std::string & id3) {
                        if (return_success) {
                          RCLCPP_INFO(get_logger(), "[%s] Returned to Loading Dock.", id3.c_str());
                        } else {
                          RCLCPP_WARN(get_logger(), "[%s] Failed to return to Loading Dock.", id3.c_str());
                        }
                      });
                  } else {
                    RCLCPP_WARN(get_logger(), "[%s] Failed to reach Machine M4.", id2.c_str());
                  }
                });
            } else {
              RCLCPP_WARN(get_logger(), "[%s] Failed to reach Machine M3.", id.c_str());
            }
          });
      } else {
        RCLCPP_WARN(get_logger(), "[%s] Failed to reach Loading Dock.", robot_id.c_str());
      }
    });
}

// ── Core goal dispatch method ─────────────────────────────────────────────────
void MissionController::sendGoal(
  const std::string & robot_ns,
  const Waypoint & waypoint,
  NavigationCallback on_complete)
{
  auto client = getClient(robot_ns);
  if (!client) {
    RCLCPP_ERROR(get_logger(), "No action client for namespace: %s", robot_ns.c_str());
    return;
  }

  // Wait up to 10 seconds for the Nav2 action server to be available
  if (!client->wait_for_action_server(10s)) {
    RCLCPP_ERROR(get_logger(),
      "[%s] NavigateToPose action server not available after 10s. "
      "Is Nav2 running?", robot_ns.c_str());
    if (on_complete) on_complete(false, robot_ns);
    return;
  }

  // Build the goal message
  auto goal_msg = NavigateToPose::Goal{};
  goal_msg.pose = makePoseStamped(waypoint);
  goal_msg.behavior_tree = "";  // Use default BT

  RCLCPP_INFO(get_logger(),
    "[%s] Sending goal → %s  (x=%.2f, y=%.2f, yaw=%.2f)",
    robot_ns.c_str(), waypoint.label.c_str(),
    waypoint.x, waypoint.y, waypoint.yaw);

  // ── Send goal options (callbacks) ─────────────────────────────────────────
  auto send_goal_options = rclcpp_action::Client<NavigateToPose>::SendGoalOptions{};

  // Feedback: print estimated time of arrival
  send_goal_options.feedback_callback =
    [this, robot_ns](
      GoalHandleNav::SharedPtr /*handle*/,
      const std::shared_ptr<const NavigateToPose::Feedback> feedback)
    {
      RCLCPP_DEBUG(get_logger(),
        "[%s] Distance remaining: %.2f m",
        robot_ns.c_str(),
        feedback->distance_remaining);
    };

  // Result: invoke the user-supplied completion callback
  send_goal_options.result_callback =
    [this, robot_ns, waypoint, on_complete](
      const GoalHandleNav::WrappedResult & result)
    {
      bool success = false;
      switch (result.code) {
        case rclcpp_action::ResultCode::SUCCEEDED:
          RCLCPP_INFO(get_logger(), "[%s] ✓ Goal '%s' SUCCEEDED.",
                      robot_ns.c_str(), waypoint.label.c_str());
          success = true;
          break;
        case rclcpp_action::ResultCode::ABORTED:
          RCLCPP_ERROR(get_logger(), "[%s] ✗ Goal '%s' ABORTED by Nav2.",
                       robot_ns.c_str(), waypoint.label.c_str());
          break;
        case rclcpp_action::ResultCode::CANCELED:
          RCLCPP_WARN(get_logger(), "[%s] ✗ Goal '%s' was CANCELED.",
                      robot_ns.c_str(), waypoint.label.c_str());
          break;
        default:
          RCLCPP_ERROR(get_logger(), "[%s] Unknown result code.", robot_ns.c_str());
          break;
      }
      if (on_complete) on_complete(success, robot_ns);
    };

  client->async_send_goal(goal_msg, send_goal_options);
}

// ── Helper: Retrieve the correct client by namespace string ───────────────────
MissionController::NavigationClient::SharedPtr
MissionController::getClient(const std::string & robot_ns)
{
  if (robot_ns == "TB3_1") return client_tb3_1_;
  if (robot_ns == "TB3_2") return client_tb3_2_;
  RCLCPP_ERROR(get_logger(), "Unknown robot namespace: '%s'", robot_ns.c_str());
  return nullptr;
}

// ── Helper: Build a PoseStamped from a Waypoint ───────────────────────────────
geometry_msgs::msg::PoseStamped
MissionController::makePoseStamped(
  const Waypoint & waypoint,
  const std::string & frame_id) const
{
  geometry_msgs::msg::PoseStamped pose;
  pose.header.stamp    = now();
  pose.header.frame_id = frame_id;
  pose.pose.position.x = waypoint.x;
  pose.pose.position.y = waypoint.y;
  pose.pose.position.z = 0.0;
  pose.pose.orientation = yawToQuaternion(waypoint.yaw);
  return pose;
}

}  // namespace dual_robot_nav

// ── main ──────────────────────────────────────────────────────────────────────
int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<dual_robot_nav::MissionController>());
  rclcpp::shutdown();
  return 0;
}