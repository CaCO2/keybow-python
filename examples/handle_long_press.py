#!/home/pi/dailyenv/bin/python
import keybow
import time
import subprocess
import math
import colorsys

class KeyboardController:
    def __init__(self):
        keybow.setup(keybow.MINI)
        self.press_start_times = {}
        self.last_action_time = time.time()
        self.breathing_step = 0
        self.hue_step = 0
        self.is_key_pressed = False
        
        # Register the handle_key method as a callback
        keybow.on(handler=self.handle_key)

    def hsv_to_rgb(self, h, s, v):
        """Convert HSV color values to RGB"""
        rgb = colorsys.hsv_to_rgb(h, s, v)
        return tuple(int(x * 255) for x in rgb)

    def breathing_effect(self):
        """Calculate breathing effect value"""
        speed = 2
        brightness = (math.sin(self.breathing_step * speed) + 1) / 20
        self.breathing_step += 0.01
        return brightness

    def update_idle_leds(self):
        current_time = time.time()
        
        if not self.is_key_pressed and (current_time - self.last_action_time) > 10:
            brightness = self.breathing_effect()
            self.hue_step = (self.hue_step + 0.001) % 1.0
            rgb = self.hsv_to_rgb(self.hue_step, 1.0, brightness)
            
            for i in range(3):
                keybow.set_led(i, *rgb)
            return True
        return False

    def shutdown_system(self):
        print("Shutting down...")
        subprocess.call("sudo poweroff", shell=True)

    def handle_key(self, index, state, is_long_press):
        self.is_key_pressed = state
        self.last_action_time = time.time()

        if state:  # Pressed
            keybow.set_led(index, 25, 25, 25)
        else:  # Released
            if index == 0 and is_long_press:  # First key long press
                print("Long press - Shutdown initiated")
                keybow.clear()
                keybow.show()
                self.shutdown_system()
            elif index == 1 and is_long_press:  # Second key long press
                # Add your action here
                pass
            elif index == 2 and is_long_press:  # Third key long press
                # Add your action here
                pass
            keybow.set_led(index, 0, 0, 0)

    def run(self):
        try:
            while True:
                self.update_idle_leds()
                keybow.show()
                time.sleep(1.0 / 24.0)  # ~24 FPS
        except KeyboardInterrupt:
            print("\nExiting...")
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        keybow.clear()
        keybow.show()

if __name__ == "__main__":
    controller = KeyboardController()
    controller.run()
