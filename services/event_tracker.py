class EventState:
    IS_IDLE = "IS_IDLE"
    EVENT_ACTIVE = "EVENT_ACTIVE"

class EventTracker:
    def __init__(self, idle_threshold_frames: int = 150):
        self.state = EventState.IS_IDLE
        self.active_classes = set()
        self.no_target_frame_count = 0
        self.idle_threshold_frames = idle_threshold_frames

    def update(self, detections: list[dict]) -> tuple[bool, list[str]]:
        """
        Updates the tracker with the current frame's YOLO detections.
        Returns:
            - A tuple: (vlm_trigger_required: bool, triggered_classes: list[str])
        """
        # Filter detections to targets of interest with conf >= 0.5
        current_classes = {
            det["label"].lower()
            for det in detections
            if det.get("confidence", 0.0) >= 0.5
        }

        if len(current_classes) > 0:
            # We see a target object in the frame, reset the idle frame counter
            self.no_target_frame_count = 0

            if self.state == EventState.IS_IDLE:
                # Transition to EVENT_ACTIVE
                self.state = EventState.EVENT_ACTIVE
                self.active_classes = current_classes.copy()
                print(f"[EventTracker] State changed to EVENT_ACTIVE. Trigger classes: {list(current_classes)}")
                return True, list(current_classes)

            elif self.state == EventState.EVENT_ACTIVE:
                # Exceptional Trigger: check if a completely new target class appeared
                new_classes = current_classes - self.active_classes
                if len(new_classes) > 0:
                    self.active_classes.update(new_classes)
                    print(f"[EventTracker] Exceptional trigger during EVENT_ACTIVE. New classes detected: {list(new_classes)}")
                    return True, list(new_classes)

        else:
            # No targets detected in the current frame
            if self.state == EventState.EVENT_ACTIVE:
                self.no_target_frame_count += 1
                if self.no_target_frame_count >= self.idle_threshold_frames:
                    # Transition to IS_IDLE
                    self.state = EventState.IS_IDLE
                    self.active_classes.clear()
                    self.no_target_frame_count = 0
                    print("[EventTracker] State changed to IS_IDLE. Event tracking reset.")

        return False, []
