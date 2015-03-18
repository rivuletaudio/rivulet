#import <Cocoa/Cocoa.h>

@interface AppDelegate : NSObject <NSApplicationDelegate> {
  NSStatusItem *statusItem;
  NSMenu *statusMenu;
  NSMenuItem *serverInfo;
  NSMenuItem *toggleServerBtn;
  NSMenuItem *quitBtn;
  
  NSTask *backend;
  NSTimer *killTimer;
}

@end

