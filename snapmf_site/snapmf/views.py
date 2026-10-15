import csv
import json
from pathlib import Path
from typing import Dict, Optional
from uuid import UUID

from django.conf import settings
from django.core.serializers import serialize
from django.http import HttpRequest, HttpResponse, JsonResponse, FileResponse
from django.http.response import (
    HttpResponseBadRequest,
    HttpResponseNotAllowed,
    HttpResponseNotFound,
)
from django.shortcuts import render
from django.utils.datastructures import MultiValueDictKeyError

from snapmf.config import AtlasFilter, Parameters

from .models import Job, FileFormat
from .tasks import run_snapms_gnps, run_snapms_masslist, run_snapmf


def docs(request: HttpRequest) -> HttpResponse:
    """View for docs page"""
    context = dict(page_name="SnapMS Documentation")
    return render(request, "docs.html", context)


def dashboard(request: HttpRequest) -> HttpResponse:
    """View for dashboard page"""
    context = dict(page_name="SNAPMS2")
    return render(request, "dashboard.html", context)


def handle_snapms(request: HttpRequest) -> HttpResponse:
    """Handle post of SnapMS passing to handler function"""
    if request.method == "POST":
        return handle_snapms_request(request)
    return HttpResponseNotAllowed(["POST"])


def job_output(request: HttpRequest, job_id: UUID) -> HttpResponse:
    """Handle access of Job output and status in HTML form"""
    job_data = get_job_data(job_id)
    context = dict(job=job_data, job_id=job_id)
    if "application/json" in request.META["HTTP_ACCEPT"]:
        return JsonResponse(context)
    return render(request, "output.html", context)


def download_output(request: HttpRequest, job_id: UUID, fmt: str) -> HttpResponse:
    """Handle sending output file"""
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    try:
        fmt = FileFormat(fmt)
        if get_job_data(job_id) is None:
            return HttpResponseNotFound("Job does not exist")
        return send_job_output(job_id, fmt)
    except ValueError:
        return HttpResponseBadRequest("File format is not available")


### Helper functions
def send_job_output(job_id: UUID, fmt: FileFormat) -> HttpResponse:
    job_dir = Path(settings.SNAPMS_DATADIR) / str(job_id)
    if fmt == FileFormat.cytoscape:
        output_file = job_dir / "snapmf.cys"
    elif fmt == FileFormat.graphml:
        output_file = find_graphml_output(job_dir)
    fname = f"snapms_{job_id}{output_file.suffix}"
    return FileResponse(output_file.open("rb"), filename=fname)


def find_graphml_output(job_dir: Path) -> Path:
    for ftype in (".zip", ".graphml"):
        flist = list(job_dir.glob(f"*{ftype}"))
        if flist:
            return flist[0]


def get_job_data(job_id: UUID) -> Optional[Dict]:
    try:
        job = Job.objects.get(id=str(job_id))
        return serialize("python", [job])[0]
    except Job.DoesNotExist:
        return None


def handle_snapms_request(request: HttpRequest) -> HttpResponse:
    """Method for handling work of creating a new job and passing to worker queue"""
    # from collections import defaultdict

    # data = defaultdict(str)
    data = json.loads(request.POST["metadata"])
    # Try to get the file
    try:
        upload_file = request.FILES["file"]
    except MultiValueDictKeyError:
        upload_file = None
    # Create Job
    if data["analysis_mode"] == "snapms":
        job = Job.objects.create(
            inputfile=upload_file or "masslist.csv",
            parameters=json.dumps(data),
        )
    elif data["analysis_mode"] == "snapmf":
        job = Job.objects.create(
            inputfile="formulalist.csv",
            parameters=json.dumps(data),
        )
    else:
        return HttpResponseBadRequest("Invalid analysis mode")
    job_id = str(job.id)
    # Setup job directory
    job_dir = Path(settings.SNAPMS_DATADIR) / job_id
    job_dir.mkdir()
    # If no upload_file, convert masslist to csv file
    # If upload_file, save to jobdir
    if upload_file is not None:
        input_file = job_dir.joinpath(upload_file.name)
        with input_file.open("wb") as f:
            for chunk in upload_file.chunks():
                f.write(chunk)
    else:
        if data["analysis_mode"] == "snapms":
            input_file = save_convert_masslist(data["masslist"], job_dir)
        elif data["analysis_mode"] == "snapmf":
            input_file = save_convert_formulalist(data["formulalist"], job_dir)
        else:
            raise ValueError("Invalid analysis mode")
    if data["reference_db"] == "coconut":
        db_path = settings.COCONUT_FILE
    else:
        db_path = settings.NPATLAS_FILE

    parameters = Parameters(
        analysis_mode=data["analysis_mode"],
        file_path=input_file,
        atlas_db_path=db_path,
        output_path=job_dir,
        ppm_error=int(data["ppm_error"]),
        adduct_list=data["adduct_list"],
        remove_duplicates=data["remove_duplicates"],
        min_gnps_size=int(data["min_gnps_size"]),
        max_gnps_size=int(data["max_gnps_size"]),
        min_atlas_size=int(data["min_atlas_size"]),
        min_group_size=int(data["min_group_size"]),
        max_edge_count=int(data["max_edge_count"]),
        max_node_count=int(data["max_node_count"]),
        job_id=job_id,
        atlas_filter=AtlasFilter(data["reference_db"]),
        custom_filter=data["custom_value"],
    )
    if parameters.file_type == "csv":
        if parameters.file_name == "mass_list":
            run_snapms_masslist.delay(parameters, job_id)
        elif parameters.file_name == "formula_list":
            run_snapmf.delay(parameters, job_id)
    elif parameters.file_type == "graphml":
        parameters.compress_output = True
        run_snapms_gnps.delay(parameters, job_id)
    elif parameters.file_type == "cys":
        return HttpResponseBadRequest("Cytoscape import is not yet supported")
    else:
        return HttpResponseBadRequest("Input file format not supported")
    return HttpResponse(json.dumps(dict(success=True, job_id=job_id)))


def save_convert_masslist(masslist: str, job_dir: Path) -> Path:
    """Take a masslist for the front end and convert to a CSV file, returning the Path"""
    mfile = job_dir / "mass_list.csv"
    with mfile.open("w") as f:
        csvwriter = csv.writer(f)
        csvwriter.writerow(["m/z"])
        csvwriter.writerows([[float(x)] for x in masslist.split("\n") if x])
    return mfile


def save_convert_formulalist(formulalist: str, job_dir: Path) -> Path:
    """Take a formulalist for the front end and convert to a CSV file, returning the Path"""
    mfile = job_dir / "formula_list.csv"
    with mfile.open("w") as f:
        csvwriter = csv.writer(f)
        csvwriter.writerow(["formula"])
        csvwriter.writerows([[x] for x in formulalist.split("\n") if x])
    return mfile