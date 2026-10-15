import shutil
from django_rq import job
from time import sleep
from snapmf import (
    Parameters,
    create_gnps_network_annotations,
    network_from_mass_list,
    network_from_formula_list,
    import_atlas,
)
from .models import Job, Status


def cleanup_job(params: Parameters, status: Status = Status.completed):
    """Cleanup input files and remove failed job data"""
    # remove input file
    params.file_path.unlink()
    if status == Status.failed:
        shutil.rmtree(params.output_path)


def mark_status(job_id: str, status: Status):
    """Change the status of a job given the job_id"""
    job = Job.objects.get(id=job_id)
    job.status = status.value
    job.save()


def run_snapms(snapms_fn, params, job_id):
    """Wrapper function to run the core SnapMS functionality
    Requires the specified function to run, params, and job_id
    """
    print("Running SnapMS for ", job_id)
    print(f"Parameters: {params.__dict__}")
    try:
        mark_status(job_id, Status.running)
        atlas = import_atlas(params)
        snapms_fn(atlas, params)
        cleanup_job(params)
        sleep(5)
        print("Completed SnapMS for ", job_id)
        mark_status(job_id, Status.completed)
    except Exception as e:
        print("SnapMS failed for ", job_id)
        print(e)
        mark_status(job_id, Status.failed)
        cleanup_job(params, Status.failed)


@job("high")
def run_snapmf(params: Parameters, job_id: str) -> None:
    run_snapms(network_from_formula_list, params, job_id)

@job("high")
def run_snapms_masslist(params: Parameters, job_id: str) -> None:
    run_snapms(network_from_mass_list, params, job_id)


@job("default")
def run_snapms_gnps(params: Parameters, job_id: str) -> None:
    run_snapms(create_gnps_network_annotations, params, job_id)
