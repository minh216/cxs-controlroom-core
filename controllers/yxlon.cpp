// minimal FXE example

#include <iostream>
#include "FXEStdInterface.h"
using namespace std;

void FXECALL valueCallback(long id, void *data, long /*datalen*/) {
  long lDataLen(0);
  FXEGetDataLength(id, &lDataLen);
  cout << "Value ID: " << id << endl;
}

void FXECALL statusCallback(long id, bool status) {
  cout << "Status ID: " << id << endl;
}

int main(int argc, char ** argv) {
  FXEInit(&valueCallback, &statusCallback);
  while(!FXECheckHwLinkStatus()) {
    cout << "Waiting for HW link status" << endl;
  }
  cout << "HW link established: " << FXECheckHwLinkStatus() << endl;
  bool hwStatus;
  auto err = FXEGetStatus(ID_STATUS_HWLINK_READY, hwStatus);
  if(!err) {
    auto err = FXEExecuteControlCommand(ID_XRAY_ON, false);
  }
}
