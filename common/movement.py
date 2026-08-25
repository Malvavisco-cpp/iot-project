import math
import random

class Move:

    def __init__(self):
        pass

    def create_state(self, vel: float, alpha_1: float, alpha_2: float, theta: float, duration: float) -> dict:
        """
        Create a single movement state.

        Args:
            vel (float): linear velocity in dm/s.
            alpha_1 (float): first joint/servo angle.
            alpha_2 (float): second joint/servo angle.
            theta (float): angle turned during the state, in degrees.
            duration (float): time the state lasts, in seconds.

        Returns:
            dict: the state description.
        """
        return {
            "v_dm/s": vel,
            "w_deg/s": theta / duration if duration else 0.0,
            "alpha_1": alpha_1,
            "alpha_2": alpha_2,
            "duration_s": duration
        }

    def s_movement(self, action_type: str) -> dict:
        """
        Build the sequence of states for an "S" movement: arm down, S-move, arm up.

        Args:
            action_type (str): the action label to attach to the message.

        Returns:
            dict: the message with the generated states.
        """
        states_list: list = []

        ## States Generation
        # Arm down
        time: float = random.uniform(0.0, 5.0)
        states_list.append(self.create_state(0, 0, -45, 0, time))
        print(states_list[-1])

        # S-move
        time: float = random.uniform(0.0, 5.0)
        vel: float = random.uniform(0.0, 5.0)
        states_list.append(self.create_state(vel, 0, 0, 180, time))
        print(states_list[-1])
        states_list.append(self.create_state(vel, 0, 0, -180, time))
        print(states_list[-1])

        # Arm up
        time: float = random.uniform(0.0, 5.0)
        states_list.append(self.create_state(0, 45, -45, 0, time))
        print(states_list[-1])

        message = {
            "action": action_type,
            "name": "S_Move",
            "states": states_list
        }
        print(message)

        return message

def main():
    theta_deg = float(input("Angulo theta (deg): "))
    radius_dm = float(input("Radio (dm): "))
    time_s = float(input("Tiempo (s): "))

    theta_rad = math.radians(theta_deg)
    arc_dm = theta_rad * radius_dm
    v_dm_s = arc_dm / time_s

    print(f"Arco calculado: {arc_dm} dm")
    print(f"Velocidad lineal calculada: {v_dm_s} dm/s")

    state = Move().create_state(v_dm_s, 0, 0, theta_deg, time_s)
    print(state)


if __name__ == "__main__":
    main()