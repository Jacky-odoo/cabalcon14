# -*- coding: utf-8 -*-

from collections import defaultdict
import datetime
from odoo import api, fields, models, tools, _

class ProjectTask(models.Model):
    _inherit = 'project.task'

    plan_ini_date = fields.Date(string='Fecha Inicio')
    plan_fin_date = fields.Date(string='Fecha Fin')
    real_ini_date = fields.Date(compute="compute_real_date", string='Inicio Real', store=True, 
        help='Fecha de Inicio Real calculado desde Partes de Horas registrado por el usuario')
    real_fin_date = fields.Date(compute="compute_real_date", string='Fin Real', store=True,
        help='Fecha de Fin Real calculado desde Partes de Horas registrado por el usuario')

    @api.depends('timesheet_ids')
    def compute_real_date(self):
        for rec in self:
            if rec.timesheet_ids:
                lines = rec.timesheet_ids
                rec.real_fin_date = lines[0].date
                rec.real_ini_date = lines[len(lines) - 1].date
