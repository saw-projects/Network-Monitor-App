#!/usr/bin/env python3
import traceback

# Author: Sawyer Baar
# ONID ID: baars
# Date: 4/20/2024 (a palindrome)

import nm_tools
import json
import datetime


class NetworkMonitorTask:
    """Each NetworkMonitor class object represents one service being monitored. For each
     service monitored, an object is initialized to be passed to the worker thread. The function
     "check_service_status" can be called on the object in the worker thread.
    """
    def __init__(self, hostname, service, frequency, task_object, url=None, ip=None, port=None, query=None, dns_record=None):
        # required
        self._hostname = hostname
        self._service = service
        self._frequency = frequency
        self._task_object = task_object
        self._url = hostname
        self._ip = task_object["ip"]
        self._port = task_object["port"]
        self._query = query
        self._dns_record = dns_record
        # output
        self._status = None
        self._status_code = None
        self._return_data = None
        self._description = None
        self._timestamp = None

    # def _get_json_data(self):
    #     """Get data for each check from JSON config file.
    #     :return: None
    #     """
    #     server_data = read_json_data()[self._hostname]
    #     self._url = server_data['url']
    #     self._ip = server_data['ip']
    #     self._port = server_data['port']
    #     self._query = server_data['query']
    #     self._dns_record = server_data['record']
    #     self._parameters = server_data['parameters']
    #     self._frequency = self._parameters[self._service]['frequency']

    def get_frequency(self):
        """Return the frequency of the service monitoring."""
        return self._frequency

    def _run_check(self):
        """Chooses the appropriate function and calls it from the network monitoring examples provided by Bram Lewis
        in the Assignment page based on the network protocol (HTTP, UDP, PING, etc.) being checked.
        Set's the status, status code, and description of the check to be printed to the terminal.

        DO NOT CALL THIS FUNCTION OUTSIDE OF THIS CLASS.

        :return: Boolean (status)
        """
        if self._service == "ping":
            addr, ping_time = nm_tools.ping(self._url)
            if ping_time == None:
                self._status = False
                self._description = "Request Timed Out"
            else:
                self._status = True
                self._description = addr
        elif self._service == "traceroute":
            url = "www." + self._url
            results = nm_tools.traceroute(url)
            self._description = results
            self._status = "Traceroute"
        elif self._service == "HTTP":
            url = "http://" + self._url
            self._status, self._status_code = nm_tools.check_server_http(url)
        elif self._service == "HTTPS":
            url = "https://" + self._url
            self._status, self._status_code, self._description = nm_tools.check_server_https(url)
        elif self._service == "NTP":
            self._status, self._description = nm_tools.check_ntp_server(self._hostname)
        elif self._service == "DNS":
            self._status, self._description = nm_tools.check_dns_server_status(self._ip, self._query, self._dns_record)
        elif self._service == "TCP":
            self._status, self._description = nm_tools.check_tcp_port(self._ip, self._port)
        elif self._service == "UDP":
            self._status, self._description = nm_tools.check_udp_port(self._ip, self._port)
        else:
            print("Error: No check performed.")
        if self._service != "traceroute":
            if self._status == True:
                self._status = "  ON-LINE   "
            else:
                self._status = "**OFF-LINE**"

    def check_service_status(self):
        """Wrap the _run_check function in a try/except to catch errors and not stop
        the entire program if some data is incorrect. If there is an error, an error message will be printed.
        Called outside of this class on the NetworkMonitor class object.

        Prints status to the terminal.

        :return: None
        """
        try:
            self._run_check()
        except:
            print(f"Error: {traceback.format_exc()}")
        finally:
            timestamp = self._get_time_stamp()
            results = self._return_output(timestamp)
            # self._print_output(timestamp)
            self._status = None
            self._status_code = None
            self._return_data = None
            self._description = None
            self._timestamp = None
        return results

    def _get_time_stamp(self):
        """Get the current timestamp.
        :return: time stamp (string)
        """
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _return_output(self, timestamp):
        """Formatted status output of the NetworkMonitor class.

                :param timestamp: str
                :return: None
                """
        msg = ""
        if self._status_code != None:
            msg = msg + str(self._status_code)
        if self._description != None:
            msg = msg + " " + str(self._description)
        if msg == "":
            msg = "No description provided."
        results = f"[{self._status}] [{timestamp}]: {self._service} request to {self._hostname}. Description: {msg}"
        # push result to monitor
        return results

    def _print_output(self, timestamp):
        """Formatted status output of the NetworkMonitor class.
        :param timestamp: str
        :return: None
        """
        msg = ""
        if self._status_code != None:
            msg = msg + str(self._status_code)
        if self._description != None:
            msg = msg + " " + str(self._description)
        if msg == "":
            msg = "No description provided."
        print(f"[{self._status}] [{timestamp}]: {self._service} request to {self._hostname}\n    Description: {msg}")


def read_json_data(file_name="config_servers.json"):
    """Read JSON config data for servers and protocols to check.
    :param file_name: str (DO NOT CHANGE)
    :return: dict (from config_servers.json)
    """
    with open(file_name) as json_file:
        all_data = json.load(json_file)
        server_data = all_data["servers"]
        return server_data


# if __name__ == '__main__':
    # hostname = "www.google.com"
    # protocol = "UDP"
    # servers = [
    #     {"hostname": "www.google.com", "protocol": "UDP"},
    #     {"hostname": "www.google.com", "protocol": "HTTP"},
    #     {"hostname": "www.google.com", "protocol": "NTP"},
    #     {"hostname": "www.oregonstate.edu", "protocol": "TCP"},
    #     {"hostname": "Google DNS", "protocol": "DNS"},
    #     {"hostname": "www.nist.time.gov", "protocol": "NTP"},
    #     {"hostname": "www.google.com", "protocol": "HTTPS"}
    #
    # ]
    # for server in servers:
    #     hostname = server["hostname"]
    #     protocol = server["protocol"]
    #     network_check = NetworkMonitor(hostname, protocol)
    #     # print(network_check._frequency)
    #     # network_check.check_server()
    #
    # data = return_threads_list()
    # print(data)
