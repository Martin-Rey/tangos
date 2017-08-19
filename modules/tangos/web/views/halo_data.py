from pyramid.view import view_config
from pyramid.compat import escape
from sqlalchemy import func, and_, or_
import numpy as np

import tangos
from tangos import core

def decode_property_name(name):
    name = name.replace("_slash_","/")
    return name

def format_array(data, max_array_length=3):
    if len(data)>max_array_length:
        return "Array"
    data_fmt = []
    for d in data:
        data_fmt.append(format_data(data))
    return "["+(", ".join(data_fmt))+"]"

def format_number(data):
    if np.issubdtype(type(data), np.integer):
        return "%d" % data
    elif np.issubdtype(type(data), np.float):
        if abs(data) > 1e5 or abs(data) < 1e-2:
            return "%.2e" % data
        else:
            return "%.2f" % data

def format_data(data, request=None, relative_to=None, max_array_length=3):
    if hasattr(data,'__len__'):
        format_array(data, max_array_length)
    elif np.issubdtype(type(data), np.number):
        return format_number(data)
    elif isinstance(data, core.Halo):
        return format_halo(data, request, relative_to)
    else:
        return escape(repr(data))



def _relative_description(this_halo, other_halo) :
    if other_halo is None :
        return "null"
    elif this_halo and this_halo.id==other_halo.id:
        return "this"
    elif this_halo and this_halo.timestep_id == other_halo.timestep_id :
        return "halo %d"%(other_halo.halo_number)
    elif this_halo and this_halo.timestep.simulation_id == other_halo.timestep.simulation_id :
        return "halo %d at t=%.2e Gyr"%(other_halo.halo_number, other_halo.timestep.time_gyr)
    else :
        if (not this_halo) or abs(this_halo.timestep.time_gyr - other_halo.timestep.time_gyr)>0.001:
            return "halo %d in %8s at t=%.2e Gyr"%(other_halo.halo_number, other_halo.timestep.simulation.basename,
                                                   other_halo.timestep.time_gyr)
        else:
            return "halo %d in %8s"%(other_halo.halo_number, other_halo.timestep.simulation.basename)


def format_halo(halo, request, relative_to=None):
    if relative_to==halo or request is None:
        return _relative_description(relative_to, halo)
    else:
        link = request.route_url('halo_view', simid=halo.timestep.simulation.basename,
                                 timestepid=halo.timestep.extension,
                                 halonumber=halo.halo_number)
        return "<a href='%s'>%s</a>"%(link, _relative_description(relative_to, halo))

@view_config(route_name='gather_property', renderer='json')
def gather_property(request):
    sim = tangos.get_simulation(request.matchdict['simid'], request.dbsession)
    ts = tangos.get_timestep(request.matchdict['timestepid'], request.dbsession, sim)

    try:
        data, db_id = ts.gather_property(decode_property_name(request.matchdict['nameid']), 'dbid()')
    except Exception as e:
        return {'error': e.message, 'error_class': type(e).__name__}

    return {'timestep': ts.extension, 'data_formatted': [format_data(d, request) for d in data],
           'db_id': list(db_id) }

@view_config(route_name='get_property', renderer='json')
def get_property(request):
    sim = tangos.get_simulation(request.matchdict['simid'], request.dbsession)
    ts = tangos.get_timestep(request.matchdict['timestepid'], request.dbsession, sim)
    halo = ts.halos.filter_by(halo_number=request.matchdict['halonumber']).first()

    try:
        result = halo.calculate(decode_property_name(request.matchdict['nameid']))
    except Exception as e:
        return {'error': e.message, 'error_class': type(e).__name__}

    return {'data_formatted': format_data(result, request, halo)}
