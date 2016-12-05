sudo apt-get install libusb-1.0-devel
mkdir libftdi
cd libftdi
git clone git://developer.intra2net.com/libftdi
cd libftdi
mkdir build
cd build
cmake  -DCMAKE_INSTALL_PREFIX="/usr" ../
make
sudo make install
cd ../../
sudo rm -r libftdi
