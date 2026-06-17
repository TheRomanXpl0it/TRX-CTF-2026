#include <linux/init.h>
#include <linux/module.h>
#include <linux/device.h>
#include <linux/kernel.h>
#include <linux/version.h>
#include <linux/uaccess.h>
#include <linux/ioctl.h>
#include <linux/fs.h>
#include <linux/cred.h>
#include <linux/namei.h>
#include <linux/mutex.h>
#include <linux/sched.h>
#include <linux/workqueue.h>
#include <linux/jiffies.h>

MODULE_LICENSE("GPL");

#define CHALL_DEVICE_NAME           "chall"
#define CHALL_DEVICE_CLASS_NAME     "chall_class"

/* IOCTL command definitions */
#define IOCTL_CHALL_MAGIC               'E'
#define IOCTL_CHALL_ADD_REQUEST         _IOW(IOCTL_CHALL_MAGIC, 0, struct urequest *)
#define IOCTL_CHALL_SET_WORK            _IOW(IOCTL_CHALL_MAGIC, 3, struct urequest *)

#define CHALL_KBUF_SIZE                 0x0400
#define CHALL_KBUFS_MAX_SIZE            0x0050
#define CHALL_KREQUESTS_MAX_SIZE        0x0020


static int                        chall_major;
static struct class              *chall_dev_class  = NULL;
static struct device             *chall_dev        = NULL;

static int     chall_open(struct inode *inodep, struct file *filep);
static int     chall_release(struct inode *inodep, struct file *filep);
static long    chall_ioctl(struct file *filep, unsigned int cmd, unsigned long arg);

static DEFINE_MUTEX(chall_ctx_mutex);

static const struct file_operations chall_fops = {
    .open           = chall_open,
    .release        = chall_release,
    .unlocked_ioctl = chall_ioctl,
};


enum krequest_type {
    TYPE_READ,      
    TYPE_WRITE,
    TYPE_DELETE,
    TYPE_SET_WORK       
};

enum krequest_status {
    REQ_FREE,
    REQ_PENDING
};

union request_info {
    struct {
        size_t size;
        char* __user ubuf;
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

struct krequest {
    pid_t pid;
    uid_t uid;
    gid_t gid;
    enum krequest_type type;
    enum krequest_status status;
    union request_info info;
    struct delayed_work dwork;
};

struct urequest {
    enum krequest_type type;
    union request_info info;
    size_t req_idx;
};

enum kbuf_status {
    KBUF_FREE,
    KBUF_IN_USE
};

struct kbuf {
    pid_t pid;
    uid_t uid;
    gid_t gid;
    enum kbuf_status status;
    char buf[CHALL_KBUF_SIZE];
};

static struct krequest krequests[CHALL_KREQUESTS_MAX_SIZE] = {0};
static struct kbuf kbufs[CHALL_KBUFS_MAX_SIZE] = {0};

static long check_perms(struct krequest* kreq){
    size_t kbuf_idx;

    
    switch (kreq->type){
    case TYPE_READ:
    case TYPE_WRITE:
    case TYPE_DELETE:
        kbuf_idx = (kreq->type == TYPE_DELETE)? kreq->info.delete.kbuf_idx : kreq->info.rw.kbuf_idx;

        if(kbuf_idx >= CHALL_KBUFS_MAX_SIZE)
            return -EINVAL;

            
        if (kbufs[kbuf_idx].status == KBUF_FREE)
            return 0;

        if(kreq->uid == 0 && kreq->gid == 0)
            return 0;

        if (kbufs[kbuf_idx].uid != kreq->uid ||
            kbufs[kbuf_idx].gid != kreq->gid ||
            kbufs[kbuf_idx].pid != kreq->pid)
            return -EPERM;
        break;
    default:
        return -EINVAL;
    }

    return 0;
}

static void request_handler(struct work_struct* work)
{
    /* Get the request */
    struct krequest* kreq;
    struct kbuf* kbuf;
    size_t kbuf_idx;

    mutex_lock(&chall_ctx_mutex);

    kreq = container_of(work, struct krequest, dwork.work);

    if(check_perms(kreq) != 0)
        goto handler_exit;

    kbuf_idx = (kreq->type == TYPE_DELETE)? kreq->info.delete.kbuf_idx : kreq->info.rw.kbuf_idx;
    
    kbuf = &kbufs[kbuf_idx];

    if(kbuf->status == KBUF_FREE) {
        kbuf->status = KBUF_IN_USE;
        kbuf->uid = kreq->uid;
        kbuf->gid = kreq->gid;
        kbuf->pid = kreq->pid;
    }

    switch (kreq->type) {
    case TYPE_READ:
        if(copy_to_user(kreq->info.rw.ubuf, kbuf->buf, (kreq->info.rw.size < CHALL_KBUF_SIZE)? kreq->info.rw.size : CHALL_KBUF_SIZE))
            goto handler_exit;
        break;
    case TYPE_WRITE:
        if(copy_from_user(kbuf->buf, kreq->info.rw.ubuf, (kreq->info.rw.size < CHALL_KBUF_SIZE)? kreq->info.rw.size : CHALL_KBUF_SIZE))
            goto handler_exit;
        break;
    case TYPE_DELETE:
        kbuf->status = KBUF_FREE;
        break;
    default:
        break;
    }

handler_exit:
    mutex_unlock(&chall_ctx_mutex);
    kreq->status = REQ_FREE;
}

static long request_add(struct urequest* ureq)
{
    long fidx, i;
    
    for (i = 0, fidx = -1; i < CHALL_KREQUESTS_MAX_SIZE; ++i) {
        if (krequests[i].status == REQ_FREE){
            fidx = i;
            break;
        }
    }

    if(fidx == -1)
        return fidx;
    
    switch (ureq->type) {
    case TYPE_READ:
    case TYPE_WRITE:
    case TYPE_DELETE:
        krequests[fidx].uid = from_kuid(current_user_ns(), current_uid());
        krequests[fidx].gid = from_kgid(current_user_ns(), current_gid());
        krequests[fidx].pid = task_pid_nr(current);
        krequests[fidx].type = ureq->type;
        krequests[fidx].status = REQ_PENDING;
        krequests[fidx].info = ureq->info;
        break;
    default:
        return -1;
    }

    ureq->req_idx = fidx;

    return 0;
}

static long chall_ioctl(struct file *filep, unsigned int cmd, unsigned long arg)
{
    struct urequest ureq;
    long r = 0;

    mutex_lock(&chall_ctx_mutex);

    if (copy_from_user(&ureq, (struct urequest *)arg, sizeof(struct urequest)) != 0){
        r = -EFAULT;
        goto ioctl_exit;
    }
    
    switch (cmd) {
    case IOCTL_CHALL_ADD_REQUEST:
        if (request_add(&ureq) != 0){
            r = -ENOSPC;
            goto ioctl_exit;
        }
        
        if (copy_to_user((struct urequest * )arg, &ureq, sizeof(struct urequest)) != 0){
            r = -EFAULT;
            goto ioctl_exit;
        }

        break;
    case IOCTL_CHALL_SET_WORK:
        if (ureq.type != TYPE_SET_WORK || ureq.info.work.kreq_idx >= CHALL_KREQUESTS_MAX_SIZE){
            r = -EINVAL;
            goto ioctl_exit;
        }        
        /* Set async work*/
        INIT_DELAYED_WORK(&krequests[ureq.info.work.kreq_idx].dwork, request_handler);
        schedule_delayed_work(&krequests[ureq.info.work.kreq_idx].dwork, msecs_to_jiffies(ureq.info.work.time));
        break;
    default:
        r = -EINVAL;
    }

ioctl_exit:
    mutex_unlock(&chall_ctx_mutex);
    return r;
}

static int __init chall_init(void)
{
    unsigned long i;

    printk(KERN_INFO "chall: Initializing driver\n");

    chall_major = register_chrdev(0, CHALL_DEVICE_NAME, &chall_fops);
    if (chall_major < 0) {
        printk(KERN_ALERT "chall: Failed to register char device (%d)\n", chall_major);
        return chall_major;
    }
    printk(KERN_INFO "chall: Registered with major number %d\n", chall_major);

    chall_dev_class = class_create(CHALL_DEVICE_CLASS_NAME);

    if (IS_ERR(chall_dev_class)) {
        unregister_chrdev(chall_major, CHALL_DEVICE_NAME);
        printk(KERN_ALERT "chall: Failed to create device class\n");
        return PTR_ERR(chall_dev_class);
    }
    printk(KERN_INFO "chall: Device class created\n");

    chall_dev = device_create(chall_dev_class, NULL, MKDEV(chall_major, 0), NULL, CHALL_DEVICE_NAME);
    if (IS_ERR(chall_dev)) {
        class_destroy(chall_dev_class);
        unregister_chrdev(chall_major, CHALL_DEVICE_NAME);
        printk(KERN_ALERT "chall: Failed to create device\n");
        return PTR_ERR(chall_dev);
    }
    printk(KERN_INFO "chall: Device ready\n");

    for (i = 0; i < CHALL_KREQUESTS_MAX_SIZE; ++i)
        krequests[i].status = REQ_FREE;

    for (i = 0; i < CHALL_KBUFS_MAX_SIZE; ++i)
        kbufs[i].status = KBUF_FREE;
    
    return 0;
}

static void __exit chall_exit(void)
{
    device_destroy(chall_dev_class, MKDEV(chall_major, 0));
    class_unregister(chall_dev_class);
    class_destroy(chall_dev_class);
    unregister_chrdev(chall_major, CHALL_DEVICE_NAME);
    printk(KERN_INFO "chall: Driver unloaded\n");
}

static int chall_open(struct inode *inodep, struct file *filep)
{
    
    printk(KERN_INFO "chall: Device opened\n");
    return 0;
}

static int chall_release(struct inode *inodep, struct file *filep)
{   
    printk(KERN_INFO "chall: Device closed\n");
    return 0;
}

module_init(chall_init);
module_exit(chall_exit);
