# -*- coding: utf-8 -*-
# Copyright (c) 2018, Leam Technology Systems and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class RenovationImageSettings(Document):

    @frappe.whitelist()
    def reapply_all(self):
        from frappe.utils.background_jobs import enqueue
        from frappe.core.page.background_jobs.background_jobs import get_info as get_running_jobs

        job_name = "reapply_all_image_watermarks"

        if job_name not in [job.get("job_name") for job in get_running_jobs()]:
            from renovation_core.utils.images import reapply_all_watermarks
            enqueue(method=reapply_all_watermarks, queue="long",
                    job_name=job_name, timeout=7200)  # 2hr
            frappe.msgprint(
                "The thumbnails will be regenerated in the background."
                " Please handle CDN cache if any.")
        else:
            frappe.msgprint(
                "A reapply request is already in process, please try again later")
