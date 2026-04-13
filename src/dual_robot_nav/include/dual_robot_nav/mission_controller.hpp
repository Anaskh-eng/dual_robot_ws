// =============================================================================
// mission_controller.hpp
// Description : Interface for the MissionController node.
//               Dispatches NavigateToPose action goals to TB3_1 and TB3_2
//               independently using rclcpp_action.
// =============================================================================

#ifndef DUAL_ROBOT_NAV__MISSION_CONTROLLER_HPP_
#define DUAL_ROBOT_NAV__MISSION_CONTROLLER_HPP_

#include <memory>
#include <string>
#include <vector>
#include <functional>

#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "nav2_msgs/action/navigate_to_pose.hpp"

namespace dual_robot_nav
{

/**
 * @brief Represents a single navigation waypoint with a label for logging.
 */
struct Waypoint
{
  std::string label;
  double x;
  double y;
  double yaw;  // radians
};

/**
 * @brief MissionController sends sequential navigation goals to two TurtleBot3
 *        robots operating under /TB3_1 and /TB3_2 namespaces.
 *
 *        Goals are dispatched asynchronously; a callback fires when each
 *        robot reaches its target (or fails), allowing the mission planner
 *        to react.
 */
class MissionController : public rclcpp::Node
{
public:
  using NavigateToPose     = nav2_msgs::action::NavigateToPose;
  using GoalHandleNav      = rclcpp_action::ClientGoalHandle<NavigateToPose>;
  using NavigationClient   = rclcpp_action::Client<NavigateToPose>;
  using NavigationCallback = std::function<void(bool success, const std::string & robot_id)>;

  explicit MissionController(const rclcpp::NodeOptions & options = rclcpp::NodeOptions());

  /**
   * @brief Send a navigation goal to the specified robot.
   * @param robot_ns    Namespace of the robot, e.g. "TB3_1"
   * @param waypoint    Target pose
   * @param on_complete Callback invoked on goal completion or failure
   */
  void sendGoal(
    const std::string & robot_ns,
    const Waypoint & waypoint,
    NavigationCallback on_complete = nullptr);

private:
  // Action clients — one per robot namespace
  NavigationClient::SharedPtr client_tb3_1_;
  NavigationClient::SharedPtr client_tb3_2_;

  // Startup timer: wait for Nav2 action servers before dispatching goals
  rclcpp::TimerBase::SharedPtr startup_timer_;

  void initClients();
  void executeDemoMission();

  NavigationClient::SharedPtr getClient(const std::string & robot_ns);

  geometry_msgs::msg::PoseStamped makePoseStamped(
    const Waypoint & waypoint,
    const std::string & frame_id = "map") const;
};

}  // namespace dual_robot_nav

#endif  // DUAL_ROBOT_NAV__MISSION_CONTROLLER_HPP_