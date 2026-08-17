import os
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
import traceback

notebook_path = r"c:\git_\samsung_project\1차프로젝트\report.ipynb"
html_path = r"c:\git_\samsung_project\1차프로젝트\report.html"

print(f"Reading notebook from: {notebook_path}")
with open(notebook_path, "r", encoding="utf-8") as f:
    nb = nbformat.read(f, as_version=4)

ep = ExecutePreprocessor(timeout=600, kernel_name='python3')

try:
    print("Executing all notebook cells...")
    ep.preprocess(nb, {'metadata': {'path': r"c:\git_\samsung_project\1차프로젝트"}})
    print("Execution finished successfully!")
    
    with open(notebook_path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)
    print("Saved executed report.ipynb")

    # Export to HTML
    from nbconvert import HTMLExporter
    html_exporter = HTMLExporter()
    (body, resources) = html_exporter.from_notebook_node(nb)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(body)
    print("Saved executed report.html")

except Exception as e:
    print(f"Error during notebook execution: {e}")
    traceback.print_exc()
