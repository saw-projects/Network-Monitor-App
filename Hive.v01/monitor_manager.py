import queue
import network_monitor_task as nm_task
import json
import socket
import os
import threading
import time
from logger import Logger
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.patch_stdout import patch_stdout


class MonitorManager:
    def __init__(self, hive_node_manager):
        self.hive_node_manager = hive_node_manager
        self.config_list = []
        self.list_of_worker_threads = []
        # flags for while loops
        self._is_monitoring = False  # while loop maintaining monitoring tasks
        self._run_flag = True  # while loop keeping TCP server up
        self.stop_event = threading.Event()
        self.last_update = self.hive_node_manager.latest_config_time

        self.logger: Logger = Logger()
        self.logger.debug("MonitorManager", "MonitorManager initialized...")

    enable: bool = True

    def run(self):
        while True:
            if MonitorManager.enable:
                # check HNM for new config
                update = self.hive_node_manager.latest_config_time
                if update != self.last_update:
                    self.update_monitors()
                #     self.set_config_list()
                # # start/update monitors based on new config
                #     if self._is_monitoring:
                #         self._stop_monitoring()
                #     self._start_monitoring()

    def set_config_list(self):
        config = self.hive_node_manager.get_config()
        self.config_list = config["tasks"]

    def update_monitors(self):
        if self._is_monitoring:
            self._stop_monitoring()
        self.set_config_list()
        self._start_monitoring()

    # def stop_monitors(self):
    #     pass
    #
    # def start_monitors(self, new_config=None):
    #     self.set_config_list()
    #     pass

    def log_results(self, message):
        pass

    # TODO: Methods to start/stop/update monitoring services

    def _start_monitoring(self):
        """
        Start monitoring service, once all tasks are updated.
        """
        # Event to signal the worker thread to stop
        self.stop_event: threading.Event = threading.Event()

        nm_task_objects = []
        self.list_of_worker_threads = []
        #  create list of network monitor task objects and thread each task
        for task in self.config_list:
            # network_monitor_task
            new_nm_task_object = nm_task.NetworkMonitorTask(task["hostname"], task["service"], task["frequency"], task)
            nm_task_objects.append(new_nm_task_object)
            # threads
            worker_thread: threading.Thread = threading.Thread(target=self.monitor_worker, args=(self.stop_event, new_nm_task_object.get_frequency(), new_nm_task_object))
            worker_thread.start()
            self.list_of_worker_threads.append(worker_thread)

        self._is_monitoring = True
        print("MONITOR: Successfully started monitoring tasks.")

    def _stop_monitoring(self):
        """Stops the monitoring service from monitoring tasks.
        :return: None"""
        self.stop_event.set()
        for worker_thread in self.list_of_worker_threads:
            worker_thread.join()
        print("MONITOR: Successfully stopped monitoring tasks.")

    def set_run_flag(self, flag_state):
        """ Sets the run flag, which controls all while loops.
        :param flag_state: Boolean value (True/False)
        :return: None
        """
        print("MONITOR: Shutting down threads and monitoring service...")
        self._run_flag = flag_state

    def monitor_worker(self, stop_event: threading.Event, freq: int,
                       service_object: nm_task.NetworkMonitorTask) -> None:
        """Performs network monitoring check on the object at the given frequency.
        :param stop_event: Event to stop thread
        :param freq: time (seconds) between checks
        :param service_object: NetworkMonitorTask object
        :return: None
        """
        while not stop_event.is_set():
            print_lock = threading.Lock()
            with print_lock:
                result = service_object.check_service_status()
                self.logger.info("MonitorManager", result)
            time.sleep(freq)


if __name__ == '__main__':
    monitor = MonitorManager()
