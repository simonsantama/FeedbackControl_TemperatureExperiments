"""
Class use to connect to the FPA's data logger

"""

import visa
import sys

class DataLogger():
    """
    Creates a DataLogger class which connects to the FPA's data logger.
    """

    VISA_ADDRESS = "GPIB0::9::INSTR"
    time_out = 1000

    def __init__(self):
        """
        Initializes the class by checking that the connection is possible 
        and sending query for the ID number of the logger

        Additionally, it prints to the command window that the connection
        has been successful
        """

        rm = visa.ResourceManager()
        my_instrument = rm.open_resource(self.VISA_ADDRESS)
        idn = my_instrument.query("*IDN?")
        print(f"Successful connection to {idn}")


    def new_instrument(self):
        """
        Connects to the data logger and returns the instrument as well
        as the visa Resource Manager (used to close the connection)

        Returns:
        -------
        rm: visa.ResourceManager
            visa resource manager created by the visa library

        my_instrument: rm.open_resource()
            logger instrument from which it is possible to write commands 
            and query states.
        """

        rm = visa.ResourceManager()
        my_instrument = rm.open_resource(self.VISA_ADDRESS)

        # initial configuration
        my_instrument.write(":ABORt")
        my_instrument.write("*RST")
        my_instrument.write("*CLS")
        my_instrument.time_out = self.time_out

        # make sure the lamps are off before starting
        my_instrument.write(':SOURce:VOLTage %G,(%s)' % (0, '@304'))
        
        return (rm, my_instrument)

    def query_data_for_HRR(my_instrument):
        """
        This function queries the voltages and temperatures needed
        to calculate the HRR

        Returns:
        -------
        response: list
            list of [O2, DPT, CO, CO2, APT, Inlet_O2, RH]
        response_TCs: list
            list of [Duct_TC, Ambient_TC]

        """
        my_instrument.write(':FORMat:READing:CHANnel %d' % (1))
        my_instrument.write(':FORMat:READing:ALARm %d' % (1))
        my_instrument.write(':FORMat:READing:UNIT %d' % (1))
        my_instrument.write(':FORMat:READing:TIME:TYPE %s' % ('REL'))
        response = my_instrument.query_ascii_values(
            ':MEASure:VOLTage:DC? %s,(%s)' % (
                'AUTO', '@101,102,103,104,109,116,201'))
        response_TCs = my_instrument.query(
            ':MEASure:TEMPerature? %s,%s,(%s)' % (
                'TCouple', 'K', '@112,113'))


        return response, response_TCs
        