# micropython_ds2482

micropython library compatible with micropython ONEWIRE through I2C IO DS2482

example1 :

import machine,ds2482
i2c=machine.I2C(1)
OW = OneWireDs(i2c)
print(OW.scan())

example2 ds18x20 :

import machine,ds2482,ds18x20
i2c=machine.I2C(1)
ds = ds18x20.DS18X20(ds2482.OneWireDs(i2c))
roms = ds.scan()
ds.convert_temp()
for rom in roms:
    print('rom {} = {}C'.format(rom,ds.read_temp(rom) ))


