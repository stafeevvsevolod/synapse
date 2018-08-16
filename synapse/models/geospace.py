import synapse.exc as s_exc
import synapse.lib.types as s_types
import synapse.lib.module as s_module
import synapse.lib.syntax as s_syntax

units = {
    'mm': 1,
    'cm': 10,

    'm': 1000,
    'meters': 1000,

    'km': 1000000,
}

distrepr = (
    (1000000.0, 'km'),
    (1000.0, 'm'),
    (10.0, 'cm'),
)

class Dist(s_types.Type):

    def postTypeInit(self):
        self.setNormFunc(int, self._normPyInt)
        self.setNormFunc(str, self._normPyStr)

    def _normPyInt(self, valu):
        return valu, {}

    def _normPyStr(self, text):
        valu, off = s_syntax.parse_float(text, 0)
        unit, off = s_syntax.nom(text, off, s_syntax.alphaset)

        mult = units.get(unit.lower())
        if mult is None:
            raise s_exc.BadTypeValu(valu=text, name=self.name,
                                    mesg='invalid/unknown dist unit: %s' % (unit,))

        return int(valu * mult), {}

    def indx(self, norm):
        return norm.to_bytes(8, 'big')

    def repr(self, norm):

        for base, unit in distrepr:
            if norm >= base:
                size = norm / base
                return '%s %s' % (size, unit)

        return '%d mm' % (norm,)

class Latitude(s_types.Type):
    SCALE = 10**8  # ~1mm resolution
    SPACE = 90 * 10**8

    def postTypeInit(self):
        self.setNormFunc(int, self._normIntStr)
        self.setNormFunc(str, self._normIntStr)
        self.setNormFunc(float, self._normFloat)

    def _normFloat(self, valu):
        if valu > 90.0 or valu < -90.0:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='Latitude may only be -90.0 to 90.0')

        valu = int(valu * Latitude.SCALE) / Latitude.SCALE

        return valu, {}

    def _normIntStr(self, valu):
        try:
            valu = float(valu)
        except Exception as e:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='Invalid float format')
        return self._normFloat(valu)

    def indx(self, norm):
        return int(norm * Latitude.SCALE + Latitude.SPACE).to_bytes(5, 'big')

class LatLong(s_types.Type):

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(list, self._normPyTuple)
        self.setNormFunc(tuple, self._normPyTuple)

    def _normPyStr(self, valu):
        valu = tuple(valu.strip().split(','))
        return self._normPyTuple(valu)

    def _normPyTuple(self, valu):
        if len(valu) != 2:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='Valu must contain valid latitude,longitude')

        try:
            latv = self.modl.type('geo:latitude').norm(valu[0])[0]
            lonv = self.modl.type('geo:longitude').norm(valu[1])[0]
        except Exception as e:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg=e)

        return (latv, lonv), {'subs': {'lat': latv, 'lon': lonv}}

    def indx(self, valu):
        return self.modl.type('geo:latitude').indx(valu[0]) + self.modl.type('geo:longitude').indx(valu[1])

    def repr(self, norm, defval=None):
        return f'{norm[0]},{norm[1]}'

class Longitude(s_types.Type):
    SCALE = 10**8  # ~1mm resolution
    SPACE = 180 * 10**8

    def postTypeInit(self):
        self.setNormFunc(int, self._normIntStr)
        self.setNormFunc(str, self._normIntStr)
        self.setNormFunc(float, self._normFloat)

    def _normIntStr(self, valu):
        try:
            valu = float(valu)
        except Exception as e:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='Invalid float format')
        return self._normFloat(valu)

    def _normFloat(self, valu):

        if valu > 180.0 or valu < -180.0:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='Longitude may only be -180.0 to 180.0')

        valu = int(valu * Longitude.SCALE) / Longitude.SCALE

        return valu, {}

    def indx(self, norm):
        return int(norm * Longitude.SCALE + Longitude.SPACE).to_bytes(5, 'big')

class GeoModule(s_module.CoreModule):

    def getModelDefs(self):
        return (
            ('geo', {

                'ctors': (
                    ('geo:dist', 'synapse.models.geospace.Dist', {}, {
                        'doc': 'A geographic distance (base unit is mm)', 'ex': '10 km'
                    }),
                    ('geo:latitude', 'synapse.models.geospace.Latitude', {}, {}),
                    ('geo:longitude', 'synapse.models.geospace.Longitude', {}, {}),
                    ('geo:latlong', 'synapse.models.geospace.LatLong', {}, {
                        'doc': 'A Lat/Long string specifying a point on Earth',
                        'ex': '-12.45,56.78'
                    }),
                ),

                'types': (

                    ('geo:nloc', ('comp', {'fields': (('ndef', 'ndef'), ('latlong', 'geo:latlong'), ('time', 'time'))}), {
                        'doc': 'Records a node latitude/longitude in space-time.'
                    }),

                    ('geo:place', ('guid', {}), {
                        'doc': 'A GUID for a geographic place.'}),
                ),

                'forms': (

                    ('geo:nloc', {}, (

                        ('ndef', ('ndef', {}), {'ro': True,
                            'doc': 'The node with location in geo/time'}),

                        ('ndef:form', ('str', {}), {'ro': True,
                            'doc': 'The form of node referenced by the ndef.'}),

                        ('latlong', ('geo:latlong', {}), {'ro': True,
                            'doc': 'The latitude/longitude the node was observed.'}),

                        ('time', ('time', {}), {'ro': True,
                            'doc': 'The time the node was observed at location'}),

                    )),

                    ('geo:place', {}, (

                        ('name', ('str', {'lower': 1, 'onespace': 1}), {
                            'doc': 'The name of the place.'}),

                        ('desc', ('str', {}), {
                            'doc': 'A long form description of the place.'}),

                        ('loc', ('loc', {}), {
                            'doc': 'The geo-political location string for the node.'}),

                        ('latlong', ('geo:latlong', {}), {
                            'doc': 'The lat/long position for the place.'}),

                        ('radius', ('geo:dist', {}), {
                            'doc': 'An approximate radius to use for bounding box calculation.'}),
                    )),
                )
            }),
        )
