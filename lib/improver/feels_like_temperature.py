# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# (C) British Crown Copyright 2017-2018 Met Office.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""Module containing feels like temperature calculation plugins"""

import numpy as np

from improver.psychrometric_calculations.psychrometric_calculations \
     import WetBulbTemperature


class WindChill(object):
    """
    This class calculates the wind chill from 10 m wind speed and temperature
    based on the wind chill temperature index from the National Weather
    Service, 2001.

    References:
      Osczevski, R. and Bluestein, M. (2005). THE NEW WIND CHILL EQUIVALENT
      TEMPERATURE CHART. Bulletin of the American Meteorological Society,
      86(10), pp.1453-1458.

      Osczevski, R. and Bluestein, M. (2008). Comments on Inconsistencies in
      the New Windchill Chart at Low Wind Speeds. Journal of Applied
      Meteorology and Climatology, 47(10), pp.2737-2738.
    """

    def __init__(self):
        """Initialise the class."""
        pass

    def __repr__(self):
        """Represent the configured plugin instance as a string."""
        result = ('<WindChill>')
        return result

    @staticmethod
    def process(temperature, wind_speed):
        """
        Calculates the wind chill. While the wind chill index is often not used
        for wind speeds greater than 5 km/h, there is no upper limit for the
        wind speed.

        Args:
          temperature (iris.cube.Cube):
            Cube of air temperatures (K)

          wind_speed (iris.cube.Cube):
            Cube of 10m wind speeds (m/s)

        Returns:
          wind_chill (iris.cube.Cube):
            Cube of wind chill temperatures (K)
        """
        # convert temperature units
        temperature.convert_units('celsius')

        # convert wind speed to km/h
        wind_speed.convert_units('km h-1')
        eqn_component = (wind_speed.data)**0.16
        wind_chill_data = (13.12 + 0.6215*temperature.data-11.37*eqn_component
                           + 0.3965*temperature.data*eqn_component)
        wind_chill = temperature.copy(wind_chill_data)
        wind_chill.rename("wind_chill")
        wind_chill.convert_units('K')

        # convert temperature units back
        temperature.convert_units('K')
        # convert wind speed to km/h back
        wind_speed.convert_units('m s-1')

        return wind_chill


class ApparentTemperature(object):
    """
    Calculates the apparent temperature from 10 m wind speed, temperature
    and actual vapour pressure using the linear regression equation
    for shade described in A Universal Scale of Apparent Temperature,
    Steadman, 1984.

    The paper calculates apparent temperature for wind speeds up to 20 m/s.
    Here, the apparent temperature regression equation has been used for all
    wind speeds.

    References:
      Steadman, R. (1984). A Universal Scale of Apparent Temperature.
      Journal of Climate and Applied Meteorology, 23(12), pp.1674-1687.
    """

    def __init__(self):
        """Initialise the class."""
        pass

    def __repr__(self):
        """Represent the configured plugin instance as a string."""
        result = ('<ApparentTemperature>')
        return result

    @staticmethod
    def process(temperature, wind_speed, relative_humidity, pressure):
        """
        Calculates the apparent temperature.
        Looks up a value for the saturation vapour pressure of water vapour
        using the temperature and a table of values. These tabulated values
        are found using lookup_svp and are corrected to the saturated
        vapour pressure in air using pressure_correct_svp both from the
        WetBulbTemperature plugin which makes use of the Goff-Gratch method.

        Args:
          temperature (iris.cube.Cube):
            Cube of air temperatures (K)

          wind_speed (iris.cube.Cube):
            Cube of 10m wind speeds (m/s)

          relative_humidity (iris.cube.Cube):
            Cube of relative humidities (fractional)

          pressure (iris.cube.Cube):
            Cube of air pressure (Pa)

        Returns:
          apparent_temperature (iris.cube.Cube):
            Cube of apparent temperatures (K)
        """

        # look up saturated vapour pressure
        svp = WetBulbTemperature().lookup_svp(temperature)
        # convert to SVP in air
        svp = WetBulbTemperature().pressure_correct_svp(
            svp, temperature, pressure)
        # calculate actual vapour pressure
        # and convert relative humidities to fractional values
        avp_data = svp.data*relative_humidity.data
        avp = svp.copy(avp_data)
        avp.rename("actual_vapour_pressure")
        avp.convert_units('kPa')
        # convert temperature units
        temperature.convert_units('celsius')
        # calculate apparent temperature
        apparent_temperature_data = (
            -2.7 + 1.04*temperature.data + 2.0*avp.data
            - 0.65*wind_speed.data)

        apparent_temperature = temperature.copy(apparent_temperature_data)
        apparent_temperature.rename("apparent_temperature")
        apparent_temperature.convert_units('K')

        return apparent_temperature


class FeelsLikeTemperature(object):
    """
    Plugin to calculate the feels like temperature using a combination of
    the wind chill index and Steadman's apparent temperature equation.
    """
    def __init__(self):
        """Initialise the class."""
        pass

    def __repr__(self):
        """Represent the configured plugin instance as a string."""
        result = ('<FeelsLikeTemperature>')
        return result

    @staticmethod
    def process(temperature, wind_speed, relative_humidity, pressure):
        """
        Calculates the feels like temperature using the following methods:

        If temperature < 10 degress C: The feels like temperature is equal to
        the wind chill.

        If temperature > 20 degress C: The feels like temperature is equal to
        the apparent temperature.

        If 10 <= temperature <= 20 degrees C: A weighting (alpha) is calculated
        in order to blend between the wind chill and the apparent temperature.

        Args:
          temperature (iris.cube.Cube):
            Cube of air temperatures (K)

          wind_speed (iris.cube.Cube):
            Cube of 10m wind speeds (m/s)

          relative_humidity (iris.cube.Cube):
            Cube of relative humidities (fractional)

          pressure (iris.cube.Cube):
            Cube of air pressure (Pa)

        Returns:
          feels_like_temperature (iris.cube.Cube):
            Cube of feels like temperatures (K)

        """
        wind_chill = WindChill().process(temperature, wind_speed)
        apparent_temperature = ApparentTemperature().process(
            temperature, wind_speed, relative_humidity, pressure)

        temperature.convert_units('celsius')
        wind_chill.convert_units('celsius')
        apparent_temperature.convert_units('celsius')

        t_data = temperature.data
        feels_like_temperature_data = np.zeros(t_data.shape)
        alpha = np.zeros(t_data.shape)

        # if temperature < 10:
        feels_like_temperature_data[t_data < 10] = wind_chill.data[t_data < 10]

        # if temperature >= 10 and <= 20:
        # calculate weighting and blend between wind chill index
        # and Steadman equation
        alpha = (t_data-10.0)/10.0
        temp_flt = (
            alpha*apparent_temperature.data + ((1-alpha)*wind_chill.data))
        t_data_between = (t_data >= 10) & (t_data <= 20)
        feels_like_temperature_data[t_data_between] = temp_flt[t_data_between]

        # if temperature > 20:
        feels_like_temperature_data[t_data > 20] = (
            apparent_temperature.data[t_data > 20])

        feels_like_temperature = temperature.copy(feels_like_temperature_data)
        feels_like_temperature.rename("feels_like_temperature")
        feels_like_temperature.convert_units('K')
        return feels_like_temperature
