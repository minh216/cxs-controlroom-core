sudo apt-get install -y libusb-1.0-0-dev
git clone git://developer.intra2net.com/libftdi
cd libftdi
mkdir build
cd build
cmake  -DCMAKE_INSTALL_PREFIX="/usr" ../
make
sudo make install
cd ../../
sudo rm -r libftdi
