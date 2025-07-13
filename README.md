# ocp_resource_report
#OpenShift Resource Reporting Tool
This Python-based tool automates the collection and analysis of OpenShift (OCP) cluster resource data, providing insights into resource quotas, pod limits, and overall resource management practices. It generates a comprehensive Excel report with detailed data sheets and visual charts for quick understanding.


# Features
- This tool provides a comprehensive overview of your OpenShift cluster's resource landscape:
- Namespace Quotas Overview: Detailed breakdown of all resource quotas configured across every namespace.
- Pod Limits and Requests: Granular report listing pods, containers, and their explicitly set CPU/memory limits/requests.
- Containers with No Limits: Identifies containers without explicitly defined CPU or memory limits, highlighting potential resource hogs.
- Namespaces with No Quota: Lists namespaces lacking any resource quotas, indicating areas for governance review.
- Quota Ratio Chart: A pie chart visualizing the ratio of namespaces with and without quotas.
  -  Green: Namespaces with quotas.
  -  Red: Namespaces without quotas.
- Limits Ratio Chart: A pie chart showing the ratio of containers with and without defined limits.
  -  Green: Containers with limits.
  -  Red: Containers without limits.

# Getting Started
Follow these steps to set up and run the reporting tool.

## Prerequisites
Before you begin, ensure you have the following installed and configured:

- Python 3.x: Download and install Python from python.org.

- OpenShift CLI (oc)

Ensure you are logged into your OpenShift cluster with an account that has sufficient permissions to get resourcequotas, pods, and namespaces across all projects (-A flag). You can test your login with oc whoami.

# Installation
- Clone the repository (or save the script):
~~~
git clone https://github.com/your-repo/ocp-resource-reporting.git
cd ocp-resource-reporting
~~~
- Since you have the script directly, save the provided Python code as `ocp_resource_report.py` in your desired directory.

- Install Python Dependencies:
Navigate to the directory where you saved `ocp_resource_report.py` and install the required libraries:
~~~
pip install pandas openpyxl matplotlib
~~~
# Usage
To generate the OpenShift resource report:

- Ensure you are logged into your OpenShift cluster via the oc CLI.
~~~
oc login --token=<your_token> --server=<your_api_server>
# Or use your preferred login method
~~~
- Run the script:
Execute the Python script from your terminal:
~~~
python ocp_resource_report.py
~~~
The script will output debug information to the console as it collects data and generates charts. Upon successful completion, an Excel file named ocp_resource_report_YYYYMMDD_HHMMSS.xlsx (e.g., ocp_resource_report_20250713_140000.xlsx) will be created in the same directory.

# Report Structure
1. The generated Excel file will contain the following sheets:

2. Quota Ratio Chart: Pie chart visualizing namespace quota distribution.

3. Limits Ratio Chart: Pie chart visualizing container limit distribution.

4. Namespace Quotas: Tabular data of all configured resource quotas.

5. Pod Limits and Requests: Tabular data of resource limits and requests for all containers within pods.

6. Containers with No Limits: Tabular data of containers lacking CPU/memory limits.

7. Namespaces with No Quota: Tabular data of namespaces without any resource quotas.

#Benefits
- Enhanced Visibility: Centralized view of resource allocations and consumption.

- Proactive Capacity Planning: Informs future resource allocation decisions.

- Improved Resource Utilization: Identifies inefficient applications and promotes best practices.

- Reduced Quota Requests: Proactively addresses bottlenecks and reduces reactive requests.

- Adherence to Best Practices: Fosters a more stable and predictable shared environment.


