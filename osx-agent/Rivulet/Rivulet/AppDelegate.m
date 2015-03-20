#import "AppDelegate.h"
#import <sys/types.h>
#import <sys/socket.h>
#import <netinet/in.h>
#import <netdb.h>

@interface AppDelegate ()

@property (weak) IBOutlet NSWindow *window;
@end

@implementation AppDelegate

NSString* notRunningUIText = @"Server is not running";
NSString* terminatingUIText = @"Stopping server...";
NSString* runningUIText = @"Listening on port 9074";
NSString* startServerUIText = @"Start server";
NSString* stopServerUIText = @"Stop server";
NSString* portBusyUIText = @"port 9074 is not available";

- (void)applicationDidFinishLaunching:(NSNotification *)aNotification {
  
  statusItem = [[NSStatusBar systemStatusBar] statusItemWithLength:NSVariableStatusItemLength];
  [statusItem setImage:[NSImage imageNamed:@"status"]];
  
  statusMenu = [[NSMenu alloc] initWithTitle:@""];
  serverInfo = [[NSMenuItem alloc] initWithTitle:notRunningUIText action:NULL keyEquivalent:@""];
  toggleServerBtn = [[NSMenuItem alloc] initWithTitle:startServerUIText action:@selector(toggleServerAction) keyEquivalent:@""];
  quitBtn = [[NSMenuItem alloc] initWithTitle:@"Quit Rivulet" action:@selector(quitApp) keyEquivalent:@""];
  
  [statusMenu addItem: serverInfo];
  [statusMenu addItem: toggleServerBtn];
  [statusMenu addItem: quitBtn];
  
  [statusItem setMenu:statusMenu];
  
}

- (BOOL)isPortAvailable:(short) portno {
  
  char *hostname = "127.0.0.1";
  
  int sockfd;
  struct sockaddr_in serv_addr;
  struct hostent *server;
  
  sockfd = socket(AF_INET, SOCK_STREAM, 0);
  if (sockfd < 0) {
    return NO;
  }
  
  server = gethostbyname(hostname);
  
  if (server == NULL) {
    return NO;
  }
  
  bzero((char *) &serv_addr, sizeof(serv_addr));
  serv_addr.sin_family = AF_INET;
  bcopy((char *)server->h_addr,
        (char *)&serv_addr.sin_addr.s_addr,
        server->h_length);
  
  serv_addr.sin_port = htons(portno);
  return (connect(sockfd,(struct sockaddr *) &serv_addr,sizeof(serv_addr)) < 0);
}

- (void)toggleServerAction {
  if (backend) {
    killTimer = [NSTimer scheduledTimerWithTimeInterval:10.0 target:self selector:@selector(killBackend) userInfo:nil repeats:NO];
    
    kill(backend.processIdentifier, SIGINT);
    [serverInfo setTitle:terminatingUIText];
    [toggleServerBtn setAction:nil];
    
  } else {
    
    if ([self isPortAvailable:9074]) {
      backend = [[NSTask alloc] init];
      
      backend.launchPath = @"/usr/local/bin/rivulet";
      [[NSNotificationCenter defaultCenter] addObserver:self selector:@selector(serverDidTerminate) name:NSTaskDidTerminateNotification object:backend];
      
      [backend launch];
      [serverInfo setTitle:runningUIText];
      [toggleServerBtn setTitle:stopServerUIText];
      [self openBrowser];
    } else {
      [serverInfo setTitle:portBusyUIText];
    }

  }
}

- (void)quitApp {
  [NSApp terminate:self];
}

- (void)serverDidTerminate {
  
  if (killTimer) {
    [killTimer invalidate];
    killTimer = nil;
  }

  [[NSNotificationCenter defaultCenter] removeObserver:self name:NSTaskDidTerminateNotification object:backend];
  backend = nil;

  [self setUpStartServerUI];
}

- (void)openBrowser {
  NSTask *task = [[NSTask alloc] init];
  task.launchPath = @"/usr/bin/open";
  task.arguments = @[@"http://localhost:9074"];
  [task launch];
  [task waitUntilExit];
}

- (void)killBackend {
  
  if (killTimer) {
    [killTimer invalidate];
    killTimer = nil;
  }
  
  if (backend) {
    kill(backend.processIdentifier, SIGKILL);
    backend = nil;
  }
  
  [self setUpStartServerUI];
}

- (void) setUpStartServerUI
{
  [serverInfo setTitle:notRunningUIText];
  [toggleServerBtn setTitle:startServerUIText];
  [toggleServerBtn setAction:@selector(toggleServerAction)];
}

- (void)applicationWillTerminate:(NSNotification *)aNotification {
  [self killBackend];
}

@end
