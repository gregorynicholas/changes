from __future__ import absolute_import, print_function

from datetime import datetime
from flask import current_app
from sqlalchemy import or_
from sqlalchemy.sql import func

from changes.constants import Status, Result
from changes.config import db
from changes.db.utils import try_create
from changes.models import (
    ItemOption, JobPhase, JobStep, JobPlan, TestCase, ItemStat,
    FileCoverage, FailureReason
)
from changes.queue.task import tracked_task


def abort_step(task):
    step = JobStep.query.get(task.kwargs['step_id'])
    step.status = Status.finished
    step.result = Result.aborted
    db.session.add(step)
    db.session.commit()
    current_app.logger.exception('Unrecoverable exception syncing step %s', step.id)


def is_missing_tests(step, jobplan):
    if 'snapshot' in jobplan.data:
        options = jobplan.data['snapshot']['options']
    else:
        options = dict(db.session.query(
            ItemOption.name, ItemOption.value,
        ).filter(
            ItemOption.item_id == jobplan.plan.id,
            ItemOption.name == 'build.expect-tests',
        ))

    if options.get('build.expect-tests') != '1':
        return False

    # if the phase hasn't started (at least according to metadata)
    # we can't accurately make comparisons
    if not step.phase.date_started:
        return False

    # if this is not the final phase then ignore it
    # TODO(dcramer): there is probably a better way we can be explicit about
    # this?
    jobphase_query = JobPhase.query.filter(
        JobPhase.job_id == step.job_id,
        JobPhase.id != step.phase_id,
        or_(
            JobPhase.date_started > step.phase.date_started,
            JobPhase.date_started == None,  # NOQA
        )
    )
    if db.session.query(jobphase_query.exists()).scalar():
        return False

    has_tests = db.session.query(TestCase.query.filter(
        TestCase.step_id == step.id,
    ).exists()).scalar()

    return not has_tests


def has_test_failures(step):
    return db.session.query(TestCase.query.filter(
        TestCase.step_id == step.id,
        TestCase.result == Result.failed,
    ).exists()).scalar()


def has_timed_out(step, jobplan):
    if step.status != Status.in_progress:
        return False

    if not step.date_started:
        return False

    # TODO(dcramer): we make an assumption that there is a single step
    options = jobplan.get_steps()[0].options

    timeout = int(options.get('build.timeout') or 0)
    if not timeout:
        return False

    # timeout is in minutes
    timeout = timeout * 60

    delta = datetime.utcnow() - step.date_started
    if delta.total_seconds() > timeout:
        return True

    return False


def record_coverage_stats(step):
    coverage_stats = db.session.query(
        func.sum(FileCoverage.lines_covered).label('lines_covered'),
        func.sum(FileCoverage.lines_uncovered).label('lines_uncovered'),
        func.sum(FileCoverage.diff_lines_covered).label('diff_lines_covered'),
        func.sum(FileCoverage.diff_lines_uncovered).label('diff_lines_uncovered'),
    ).filter(
        FileCoverage.step_id == step.id,
    ).group_by(
        FileCoverage.step_id,
    ).first()

    stat_list = (
        'lines_covered', 'lines_uncovered',
        'diff_lines_covered', 'diff_lines_uncovered',
    )
    for stat_name in stat_list:
        try_create(ItemStat, where={
            'item_id': step.id,
            'name': stat_name,
        }, defaults={
            'value': getattr(coverage_stats, stat_name, 0) or 0,
        })


@tracked_task(on_abort=abort_step, max_retries=100)
def sync_job_step(step_id):
    pass