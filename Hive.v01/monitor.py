import queue
import network_monitor_task as nm_task
import json
import socket
import os
import threading
import time
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.patch_stdout import patch_stdout


class MonitoringService:
    def __init__(self, port=50000):
        # initiate needed variables
        self._task_list = []
        self._results_queue = queue.Queue()  # to hold results to be sent back to MGMT
        self.list_of_worker_threads = []
        # results delay
        self.results_delay = 10  # a delay to send bundles of results to the manager
        # set address
        self._ip = "127.0.0.1"
        self._port = port
        self.set_port()
        # manager address
        self.data_ip = "127.0.0.1"
        self.data_port = 12346
        self.unique_id = None
        # flags for while loops
        self._is_monitoring = False  # while loop maintaining monitoring tasks
        self._run_flag = True  # while loop keeping TCP server up
        self.stop_event = threading.Event()
        # Start the server
        self.start_tcp_server(self._ip, self._port)

    def set_port(self):
        print("Set the port for the monitoring service.")
        while self._port <= 50000:
            self._port = int(input("Please enter a port number greater than 50000: "))

    def update_monitoring_tasks(self, task_config: dict) -> str:
        """Update self._tasks based on json config file data received from MGMT.
        :param task_config: list:
        :return: str: status
        """
        # Check if the task config matches the current task config file
        new_tasks = task_config["tasks"]
        if new_tasks == self._task_list:
            update_status = "no change"
        else:
            self._task_list = new_tasks
            update_status = "updated"
        return update_status

    def _start_monitoring(self):
        """Start monitoring service, once all tasks are updated.
        :return:
        """
        # Event to signal the worker thread to stop
        self.stop_event: threading.Event = threading.Event()

        nm_task_objects = []
        self.list_of_worker_threads = []
        #  create list of network monitor task objects and thread each task
        for task in self._task_list:
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

    def add_results(self, result):
        """ Add results to management service software queue.
        :param result:
        """
        self._results_queue.put(result)

    def set_run_flag(self, flag_state):
        """ Sets the run flag, which controls all while loops.
        :param flag_state: Boolean value (True/False)
        :return: None
        """
        print("MONITOR: Shutting down threads and monitoring service...")
        self._run_flag = flag_state

    def monitor_cli_commands(self):
        commands = ["stop", "results"]
        completer = WordCompleter(commands)
        session = PromptSession(completer=completer)
        while self._run_flag:
            # with patch_stdout():
            try:
                action = session.prompt("Monitor Command: ")
                parts = action.split()
                cmd = parts[0] if parts else ""
                if cmd == "stop":
                    self._stop_monitoring()
                    self.set_run_flag(False)
                elif cmd == "help":
                    print("Available commands: for the Monitor CLI:"
                          "\n 'stop' to stop the Monitoring service")
            except Exception as e:
                print(f"MONITOR: Error in CLI command {cmd}: {e}")

    def start_tcp_server(self, server_ip: str, server_port: int) -> None:
        """Creates a socket, listens. Once connected it continues running until shutdown.
        :param server_ip:
        :param server_port:
        :return: None
        """
        server_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((server_ip, server_port))
        server_socket.listen(5)
        server_socket.settimeout(4.0)
        print(f"MONITOR: Server started and listening on {server_ip}:{server_port}")

        # monitor for CLI prompts for testing
        monitor_cli_thread: threading.Thread = threading.Thread(target=self.monitor_cli_commands, daemon=True)
        monitor_cli_thread.start()

        # list for client threads
        client_threads = []
        data_threads = []

        try:
            while self._run_flag:
                try:
                    client_socket: socket.socket
                    client_address: tuple[str, int]
                    client_socket, client_address = server_socket.accept()
                    print(f"MONITOR: Accepted connection from client: {client_address}")

                    handle_client_thread: threading.Thread = threading.Thread(target=self.handle_client_connection, args=[client_socket], daemon=True, )
                    handle_client_thread.start()
                    client_threads.append(handle_client_thread)

                    data_thread: threading.Thread = threading.Thread(target=self.send_data, daemon=True, )
                    data_thread.start()
                    data_threads.append(data_thread)

                except Exception as e:
                    if "timed out" not in str(e):
                        print(f"MONITOR: Error in server loop: {e}")
        finally:
            monitor_cli_thread.join()
            for data_thread in data_threads:
                data_thread.join()
            for thread in client_threads:
                thread.join()
            server_socket.close()

    def handle_client_connection(self, client_socket: socket.socket) -> None:
        """Handles a client connection, listening for incoming commands and responding.
        :param client_socket:
        :return: None
        """
        try:
            while self._run_flag:
                client_message: str = client_socket.recv(1024).decode()
                # convert to JSON dict
                print(client_message)
                client_message: dict = json.loads(client_message)
                #  update config
                if client_message["command"] == "configure tasks":
                    new_configuration = client_message["configuration"]
                    task_updated = self.update_monitoring_tasks(new_configuration)
                    if task_updated == "updated":
                        return_message = f"MONITOR: Successfully updated monitoring tasks"
                        tasks = new_configuration["tasks"]
                        for task in tasks:
                            print(f"MONITOR: new task: {task}")
                        print("\n")
                        # stop the existing tasks, and re-start with new tasks
                        if self._is_monitoring:
                            self._stop_monitoring()
                        self._start_monitoring()
                    elif task_updated == "no change":
                        return_message = f"MONITOR: Existing monitoring tasks match the received configuration"
                    client_socket.sendall(return_message.encode())

                # shutdown on command from client
                elif client_message["command"] == "stop":
                    return_message = f"MONITOR: Stopping monitoring and closing connection."
                    self.set_run_flag(False)
                    self._stop_monitoring()
                    client_socket.sendall(return_message.encode())

                elif client_message["command"] == "set_unique_id":
                    self.unique_id = client_message["id"]
                    return_message = f"Unique ID set to {self.unique_id}"
                    client_socket.sendall(return_message.encode())

        except socket.error as e:
            print(f"MONITOR: Socket error with {client_socket}: {e}")
        finally:
            client_socket.close()
            print(f"MONITOR: Connection with client closed.")

    def send_data(self) -> None:
        """Handles a client connection, listening for incoming commands and responding.
        :param data_ip:
        :param data_port:
        :return: None
        """
        while self._run_flag:
            try:
                results_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                results_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                results_socket.connect((self.data_ip, self.data_port))
                message = "MONITOR ID: " + str(self.unique_id) + ","
                try:
                    count = 0
                    while not self._results_queue.empty():
                        data = self._results_queue.get()
                        count += 1
                        message = message + "," + data
                    print(f"\nMONITOR: Sending {count} result(s) to Manager.\n")
                    results_socket.sendall(message.encode())
                except socket.error as e:
                    print(f"MONITOR: Socket error with {results_socket}: {e}")
                finally:
                    results_socket.close()
                    # print(f"MONITOR: Connection with client closed.")
            except Exception as e:
                pass
            finally:
                time.sleep(self.results_delay)

    def monitor_worker(self, stop_event: threading.Event, freq: int, service_object: nm_task.NetworkMonitorTask) -> None:
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
                self.add_results(result)
            time.sleep(freq)


def read_json_data(file_name="config_tasks.json"):
    """Read JSON config data for servers and protocols to check.

    :param file_name: str (DO NOT CHANGE)
    :return: dict (from config_servers.json)
    """
    with open(file_name) as json_file:
        data = json.load(json_file)
        return data


if __name__ == '__main__':
    monitor = MonitoringService()
