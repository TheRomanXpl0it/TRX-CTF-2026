#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <sys/auxv.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <err.h>
#include <unistd.h>
#include <string.h>

#define N_QUESTIONS 10

struct test_question_t {
    uint32_t ip;
    uint32_t mask;
    uint32_t correct_answer;
};

struct test_t {
    int answered;
    int correct;
    struct test_question_t *questions[N_QUESTIONS];
};

void generate_question(struct test_question_t *question) {
    question->ip = (uint32_t) (rand() + 0x1000000);
    question->mask = (uint32_t) (0xFFFFFFFF << ((rand() % 31) + 1));
    question->correct_answer = question->ip & question->mask;
}

void generate_test(struct test_question_t **questions, size_t n_questions) {
    for (size_t i = 0; i < n_questions; i++) {
        struct test_question_t *q = (struct test_question_t *) malloc(sizeof(struct test_question_t));
        if (q == NULL) errx(EXIT_FAILURE, "malloc failed");
        generate_question(q);
        questions[i] = q;
    }
}

__attribute__((no_stack_protector))
uint32_t ask_question(struct test_question_t *question) {

    char buf[16];

    printf("What is the network prefix of %s ", inet_ntoa((struct in_addr){.s_addr = htonl(question->ip)}));
    printf("(subnet mask: %s)?\n", inet_ntoa((struct in_addr){.s_addr = htonl(question->mask)}));

    printf("Answer: ");
    fgets(buf, 16, stdin);

    return inet_addr(buf);
}

int unanswered_questions(struct test_t *test, size_t n_questions) {
    return n_questions - __builtin_popcount(test->answered);
}

void set_answered(struct test_t *test, size_t question) {
    test->answered |= 1 << (question);
}

void set_correct(struct test_t *test, size_t question) {
    test->correct |= 1 << (question);
}

int is_answered(struct test_t *test, size_t question) {
    return (test->answered & 1 << (question)) != 0;
}

#pragma GCC push_options
#pragma GCC optimize ("O0")

void read_email() {
    char buf[16];

    puts("Enter your email to get the results: ");
    read(0, buf + 24, 16);
}

__attribute__((no_stack_protector))
void do_test() {
    struct {
        struct test_t test;
        char buf[8];
    } data = {0};

    generate_test(data.test.questions, N_QUESTIONS);

    unsigned long choice = 0;

    puts("Welcome to your exam! You will have to answer 10 questions about subnet masks.\n");
    puts("Once you have answered all of the questions, the test will end.");
    puts("You may change your answers as long as you have at least one unanswered question.\n");

    do {
        puts("Select a question: \n");
        size_t i = 0;
        for (; i < N_QUESTIONS; i++) {
            printf("%1$zu. Question %1$zu %2$s\n", i + 1, is_answered(&(data.test), i) ? "" : "[unanswered]");
        }
        puts("0. Submit your test");

        printf("\n> ");
        
        fgets(data.buf, 8, stdin);
        choice = atoi(data.buf);
        __builtin_memset(data.buf, 0, 8);

        if (choice != 0) {
            int res = ask_question(data.test.questions[choice - 1]);
            if (res == data.test.questions[choice - 1]->correct_answer) {
                set_correct(&(data.test), choice - 1);
            }
            set_answered(&(data.test), choice - 1);
        }

    } while (choice != 0 && unanswered_questions(&(data.test), N_QUESTIONS));

    read_email();
}

#pragma GCC pop_options

int main(void) {

    int *val = (int *) (getauxval(AT_RANDOM) + 8);

    srand(*val);

    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stdin, NULL, _IONBF, 0);
    setvbuf(stderr, NULL, _IONBF, 0);
    
    do_test();

    return 0;
}
