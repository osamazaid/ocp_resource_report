import subprocess
import pandas as pd
import io
import datetime
import json
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import os
from openpyxl.drawing.image import Image

def run_oc_command(command):
    """
    Runs an oc command and returns its stdout.
    Handles potential errors during command execution.
    """
    print(f"DEBUG: Running command: {command}")
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, shell=True)
        print(f"DEBUG: Command stdout length: {len(result.stdout.strip())}")
        if not result.stdout.strip():
            print("DEBUG: oc command returned empty output.")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e.cmd}")
        print(f"Stderr: {e.stderr}")
        return None
    except FileNotFoundError:
        print("Error: 'oc' command not found. Please ensure OpenShift CLI is installed and in your PATH.")
        return None

def get_namespace_quotas():
    """
    Retrieves resource quotas for all namespaces using go-template.
    Returns a pandas DataFrame.
    """
    print("Collecting namespace quota data...")
    command = """oc get resourcequota -A -o=go-template='
{{range .items}}
Name:{{.metadata.name}}
Namespace:{{.metadata.namespace}}
ResourceQuota:
{{range $key, $value := .spec.hard}}  {{printf "%s=%s" $key $value}}
{{end}}---
{{end}}
'"""
    output = run_oc_command(command)

    if not output:
        print("DEBUG: get_namespace_quotas: No output from oc command.")
        return pd.DataFrame()

    data = []
    current_quota = {}
    lines = output.splitlines()
    print(f"DEBUG: get_namespace_quotas: Processing {len(lines)} lines of output.")
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith("Name:"):
            if current_quota:
                data.append(current_quota)
            current_quota = {"Name": line.replace("Name:", "").strip()}
        elif line.startswith("Namespace:"):
            current_quota["Namespace"] = line.replace("Namespace:", "").strip()
        elif line.startswith("ResourceQuota:"):
            pass
        elif line.startswith("---"):
            if current_quota:
                data.append(current_quota)
            current_quota = {}
        elif line and "=" in line:
            key, value = line.split("=", 1)
            current_quota[key.strip()] = value.strip()
            
    if current_quota and "Name" in current_quota:
        data.append(current_quota)

    df = pd.DataFrame(data)
    print(f"DEBUG: get_namespace_quotas: DataFrame has {len(df)} rows.")
    cols = ['Name', 'Namespace', 'cpu', 'memory', 'limits.cpu', 'limits.memory', 'requests.cpu', 'requests.memory', 'pods']
    existing_cols = [col for col in cols if col in df.columns]
    other_cols = [col for col in df.columns if col not in existing_cols]
    return df[existing_cols + other_cols]


def get_pod_resource_limits():
    """
    Retrieves resource limits and requests for all pods across all namespaces.
    Returns a pandas DataFrame.
    """
    print("Collecting pod resource limits and requests data...")
    command = """oc get pod -A -o=go-template='
{{range .items}}
Pod:{{.metadata.name}}
Namespace:{{.metadata.namespace}}
Containers:
{{range .spec.containers}}  Name:{{.name}},Limits:{{if .resources.limits}}{{.resources.limits}}{{else}}None{{end}},Requests:{{if .resources.requests}}{{.resources.requests}}{{else}}None{{end}}
{{end}}---
{{end}}
'"""
    output = run_oc_command(command)

    if not output:
        print("DEBUG: get_pod_resource_limits: No output from oc command.")
        return pd.DataFrame()

    data = []
    current_pod = {}
    lines = output.splitlines()
    print(f"DEBUG: get_pod_resource_limits: Processing {len(lines)} lines of output.")
    for line in lines:
        line = line.strip()
        if line.startswith("Pod:"):
            if current_pod:
                for container in current_pod.get("Containers", []):
                    row = {
                        "Pod Name": current_pod["Pod"],
                        "Namespace": current_pod["Namespace"],
                        "Container Name": container["Name"],
                        "Limits": container["Limits"],
                        "Requests": container["Requests"]
                    }
                    data.append(row)
            current_pod = {"Pod": line.replace("Pod:", "").strip(), "Containers": []}
        elif line.startswith("Namespace:"):
            current_pod["Namespace"] = line.replace("Namespace:", "").strip()
        elif line.startswith("Containers:"):
            pass
        elif line.startswith("---"):
            if current_pod:
                for container in current_pod.get("Containers", []):
                    row = {
                        "Pod Name": current_pod["Pod"],
                        "Namespace": current_pod["Namespace"],
                        "Container Name": container["Name"],
                        "Limits": container["Limits"],
                        "Requests": container["Requests"]
                    }
                    data.append(row)
            current_pod = {}
        elif line.startswith("Name:") and ",Limits:" in line and ",Requests:" in line:
            parts = line.split(",Limits:")
            container_name_part = parts[0].replace("Name:", "").strip()
            limits_requests_part = parts[1]

            limits_str, requests_str = limits_requests_part.split(",Requests:")

            # Reverting to string cleanup for "map[...]" format
            limits_str = limits_str.strip().replace("map[", "").replace("]", "").replace(" ", ", ")
            requests_str = requests_str.strip().replace("map[", "").replace("]", "").replace(" ", ", ")

            current_pod["Containers"].append({
                "Name": container_name_part,
                "Limits": limits_str if limits_str != "None" else "",
                "Requests": requests_str if requests_str != "None" else ""
            })
            
    if current_pod and "Pod" in current_pod:
        for container in current_pod.get("Containers", []):
            row = {
                "Pod Name": current_pod["Pod"],
                "Namespace": current_pod["Namespace"],
                "Container Name": container["Name"],
                "Limits": container["Limits"],
                "Requests": container["Requests"]
            }
            data.append(row)

    df = pd.DataFrame(data)
    print(f"DEBUG: get_pod_resource_limits: Final DataFrame has {len(df)} rows.")
    return df

def get_all_namespaces():
    """
    Retrieves a list of all namespaces.
    Returns a pandas DataFrame.
    """
    print("Collecting all namespace names...")
    command = "oc get ns -o=go-template='{{range .items}}{{.metadata.name}}\n{{end}}'"
    output = run_oc_command(command)
    if not output:
        print("DEBUG: get_all_namespaces: No output from oc command.")
        return pd.DataFrame(columns=['Namespace'])
    namespaces = [ns.strip() for ns in output.splitlines() if ns.strip()]
    df = pd.DataFrame(namespaces, columns=['Namespace'])
    print(f"DEBUG: get_all_namespaces: DataFrame has {len(df)} rows.")
    return df

def create_pie_chart(data_counts, title, output_path, colors=None): # Added 'colors' parameter
    """
    Creates a pie chart and saves it to a file.
    data_counts: A dictionary like {'Label1': count1, 'Label2': count2}
    colors: Optional list of colors for the pie slices.
    """
    labels = data_counts.keys()
    sizes = data_counts.values()
    
    if sum(sizes) == 0:
        print(f"DEBUG: Not enough data to create chart: {title}")
        return None

    fig1, ax1 = plt.subplots(figsize=(8, 8))
    
    def autopct_format(pct):
        total = sum(sizes)
        val = int(round(pct*total/100.0))
        return '{:.1f}%\n({:d})'.format(pct, val)

    # Use specified colors, or matplotlib's default if not provided
    wedges, texts, autotexts = ax1.pie(sizes, labels=labels, autopct=autopct_format,
                                       startangle=90, textprops=dict(color="w"), colors=colors)
    
    for autotext in autotexts:
        autotext.set_color('black')
        autotext.set_fontsize(10)

    ax1.axis('equal')
    ax1.set_title(title)
    
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close(fig1)
    print(f"DEBUG: Chart saved to {output_path}")
    return output_path

def main():
    """
    Main function to orchestrate data collection and Excel export.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_filename = f"ocp_resource_report_{timestamp}.xlsx"

    namespace_quotas_df = get_namespace_quotas()
    pod_limits_df = get_pod_resource_limits()
    all_namespaces_df = get_all_namespaces()

    print(f"\nDEBUG: namespace_quotas_df is empty: {namespace_quotas_df.empty}")
    print(f"DEBUG: pod_limits_df is empty: {pod_limits_df.empty}")
    print(f"DEBUG: all_namespaces_df is empty: {all_namespaces_df.empty}")

    # --- Prepare data for Charts ---

    # Quota Ratio Data
    namespaces_with_quotas_count = len(namespace_quotas_df['Namespace'].unique()) if not namespace_quotas_df.empty else 0
    all_namespace_names_set = set(all_namespaces_df['Namespace'].unique()) if not all_namespaces_df.empty else set()
    namespaces_without_quotas_count = len(all_namespace_names_set) - namespaces_with_quotas_count
    
    quota_ratio_data = {
        'Namespaces with Quota': namespaces_with_quotas_count,
        'Namespaces without Quota': namespaces_without_quotas_count
    }
    print(f"DEBUG: Quota Ratio Data: {quota_ratio_data}")

    # Limits Ratio Data (based on containers)
    containers_with_limits_count = 0
    containers_without_limits_count = 0
    if not pod_limits_df.empty:
        containers_with_limits_count = len(pod_limits_df[pod_limits_df['Limits'] != ''])
        containers_without_limits_count = len(pod_limits_df[pod_limits_df['Limits'] == ''])
    
    limits_ratio_data = {
        'Containers with Limits': containers_with_limits_count,
        'Containers without Limits': containers_without_limits_count
    }
    print(f"DEBUG: Limits Ratio Data: {limits_ratio_data}")


    # --- Generate Charts ---
    chart_files = []
    
    # Define colors: Green for 'with', Red for 'without'
    chart_colors = ['#4CAF50', '#FF0000'] # Green, Red

    # Quota Ratio Chart
    quota_chart_path = f'quota_ratio_chart_{timestamp}.png'
    if sum(quota_ratio_data.values()) > 0:
        created_path = create_pie_chart(quota_ratio_data, 'Ratio of Namespaces with/without Quota', quota_chart_path, colors=chart_colors)
        if created_path:
            chart_files.append(created_path)
    else:
        print("DEBUG: Skipping Quota Ratio Chart: No namespace data.")

    # Limits Ratio Chart
    limits_chart_path = f'limits_ratio_chart_{timestamp}.png'
    if sum(limits_ratio_data.values()) > 0:
        created_path = create_pie_chart(limits_ratio_data, 'Ratio of Containers with/without Limits', limits_chart_path, colors=chart_colors)
        if created_path:
            chart_files.append(created_path)
    else:
        print("DEBUG: Skipping Limits Ratio Chart: No container data.")


    # --- New Sheet 1: Containers with No Limits ---
    no_limits_df = pd.DataFrame()
    if not pod_limits_df.empty:
        no_limits_df = pod_limits_df[pod_limits_df['Limits'] == ''].copy()
        if not no_limits_df.empty:
             no_limits_df = no_limits_df[['Pod Name', 'Namespace', 'Container Name', 'Requests']]
    print(f"DEBUG: no_limits_df is empty: {no_limits_df.empty}")


    # --- New Sheet 2: Projects (Namespaces) with No Quota ---
    namespaces_without_quotas_list = sorted(list(all_namespace_names_set - set(namespace_quotas_df['Namespace'].unique()))) if not namespace_quotas_df.empty else sorted(list(all_namespace_names_set))
    no_quota_df = pd.DataFrame(namespaces_without_quotas_list, columns=['Namespace'])
    print(f"DEBUG: no_quota_df is empty: {no_quota_df.empty}")


    if namespace_quotas_df.empty and pod_limits_df.empty and no_limits_df.empty and no_quota_df.empty and not chart_files:
        print("No data collected or charts generated. Exiting.")
        return

    print(f"\nGenerating Excel report: {excel_filename}")
    try:
        with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
            # Write charts first (on separate sheets)
            if os.path.exists(quota_chart_path):
                worksheet = writer.book.create_sheet('Quota Ratio Chart', 0)
                img = Image(quota_chart_path)
                img.width = 600
                img.height = 450
                worksheet.add_image(img, 'A1')
                print(f"DEBUG: Inserted Quota Ratio Chart into Excel.")
            else:
                print(f"DEBUG: Quota Ratio Chart file not found: {quota_chart_path}")

            if os.path.exists(limits_chart_path):
                worksheet = writer.book.create_sheet('Limits Ratio Chart', 1)
                img = Image(limits_chart_path)
                img.width = 600
                img.height = 450
                worksheet.add_image(img, 'A1')
                print(f"DEBUG: Inserted Limits Ratio Chart into Excel.")
            else:
                print(f"DEBUG: Limits Ratio Chart file not found: {limits_chart_path}")
            
            if not namespace_quotas_df.empty:
                namespace_quotas_df.to_excel(writer, sheet_name='Namespace Quotas', index=False)
                print("Namespace Quotas data written to 'Namespace Quotas' sheet.")
            else:
                print("No Namespace Quota data to write.")

            if not pod_limits_df.empty:
                pod_limits_df.to_excel(writer, sheet_name='Pod Limits and Requests', index=False)
                print("Pod Limits and Requests data written to 'Pod Limits and Requests' sheet.")
            else:
                print("No Pod Limits and Requests data to write.")
            
            if not no_limits_df.empty:
                no_limits_df.to_excel(writer, sheet_name='Containers with No Limits', index=False)
                print("Containers with No Limits data written to 'Containers with No Limits' sheet.")
            else:
                print("No Containers with No Limits data to write.")

            if not no_quota_df.empty:
                no_quota_df.to_excel(writer, sheet_name='Namespaces with No Quota', index=False)
                print("Namespaces with No Quota data written to 'Namespaces with No Quota' sheet.")
            else:
                print("No Namespaces with No Quota data to write.")

        print(f"Report generation complete. File saved as {excel_filename}")
    except Exception as e:
        print(f"ERROR: Failed to write Excel file: {e}")
        print("This could be due to an older openpyxl version, or the Excel file being open.")
        print("Please ensure openpyxl is up-to-date (`pip install --upgrade openpyxl`)")

    finally:
        for chart_file in chart_files:
            try:
                os.remove(chart_file)
                print(f"DEBUG: Removed temporary chart file: {chart_file}")
            except OSError as e:
                print(f"DEBUG: Error removing temporary chart file {chart_file}: {e}")

if __name__ == "__main__":
    main()
