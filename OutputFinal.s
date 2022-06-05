	.file "OutputFinal.s"
.comm mac, 4, 4
.comm a, 16, 4
.comm b, 56, 4
.comm c, 16, 4
.comm punt, 72, 4
	movl $4, $mac #mac = assignment
main:
	pushl %ebp #Function Prologue
	movl %esp, %ebp
	subl $32, %esp #Reserve space for result (offset=-4)
	movl $0, %eax #Move return value
	movl %ebp, %esp #Function Epilogue
	popl %ebp
	ret

