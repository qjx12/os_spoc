#lab1
## 练习1
###[1-1]操作系统镜像文件ucore.img是如何一步一步生成的？


生成ucore.img的代码如下：
```
$(UCOREIMG): $(kernel) $(bootblock)
	$(V)dd if=/dev/zero of=$@ count=10000
	$(V)dd if=$(bootblock) of=$@ conv=notrunc
	$(V)dd if=$(kernel) of=$@ seek=1 conv=notrunc
```
ucore硬盘映像有10000个扇区，每个512字节，其中第一个扇区存放bootblock，从第二个扇区开始存放kernel。

因此需要先生成kernel和bootblock。

生成kernel代码如下：
```
$(kernel): tools/kernel.ld
$(kernel): $(KOBJS)
	@echo + ld $@
	$(V)$(LD) $(LDFLAGS) -T tools/kernel.ld -o $@ $(KOBJS)
	@$(OBJDUMP) -S $@ > $(call asmfile,kernel)
	@$(OBJDUMP) -t $@ | $(SED) '1,/SYMBOL TABLE/d; s/ .* / /; /^$$/d' > $(call symfile,kernel)
```

kernel依赖kernel.ld和KOBJS。
其中KOBJS为kern文件夹下所有.c文件生成的.o文件。

生成bootblock代码如下：
```
$(bootblock): $(call toobj,$(bootfiles)) | $(call totarget,sign)
	@echo + ld $@
	$(V)$(LD) $(LDFLAGS) -N -e start -Ttext 0x7C00 $^ -o $(call toobj,bootblock)
	@$(OBJDUMP) -S $(call objfile,bootblock) > $(call asmfile,bootblock)
	@$(OBJCOPY) -S -O binary $(call objfile,bootblock) $(call outfile,bootblock)
	@$(call totarget,sign) $(call outfile,bootblock) $(bootblock)
```

生成bootblock需要bootasm.o、bootmain.o、sign。

其中bootasm.o由bootasm.S生成，bootmian.o由bootmain.c生成。

生成sign：
```
$(call add_files_host,tools/sign.c,sign,sign)
$(call create_target_host,sign,sign)
```

复制bootblock.o到bootblock.out后，用sign处理生成bootblock。


###[1-2] 一个被系统认为是符合规范的硬盘主引导扇区的特征是什么?

由sign.c可知，符合规范的硬盘主引导扇区大小为512字节，其中最末两字节为0x55AA。


##练习2
###[2-1] 从 CPU 加电后执行的第一条指令开始,单步跟踪 BIOS 的执行。
1 修改 lab1/tools/gdbinit,
```
set architecture i8086
target remote :1234
```
2 在 lab1目录下，执行
```
make debug
```
这时gdb停在BIOS的第一条指令0xffff0处。

3 在看到gdb的调试界面(gdb)后，不断执行si命令，就可以单步跟踪BIOS执行了。

4 用以下指令查看BIOS的代码：
```
x /2i 0xffff0
```
得到：
```
0xffff0: ljmp $0xf000,$0xe05b
0xffff5: xor %dh,0x322f
```
进一步可以执行：
```
x /10i 0xfe05b
```
可以看到后续的BIOS代码。


###[2-2]在初始化位置0x7c00设置实地址断点,测试断点正常。
执行命令：
```
b *0x7c00
x /2i $pc
```

可得：
```
0x7c00:      cli    
0x7c01:      cld 
```

断点测试正常。

###[2-3]从0x7c00开始跟踪代码运行,将单步跟踪反汇编得到的代码与bootasm.S和 bootblock.asm进行比较。

修改lab1/tools/gdbinit
```
set architecture i8086
target remote :1234
b *0x7c00
continue
x /10i $pc
set architecture i386
```

可得反汇编代码，与bootasm.S和bootblock.asm中的代码相同。

###[2-4]自己找一个bootloader或内核中的代码位置，设置断点并进行测试。

执行指令：
```
b *0x7c01
continue
x /2i $pc
```

可设置断点于bootmain函数入口，读取前两条指令为：
```
push %ebp
mov  %esp, %ebp
```
##练习3：分析bootloader进入保护模式的过程。

跳转到0x7c00后，系统处于实模式。首先关闭中断，初始化DF和段寄存器。

为了向后兼容早期PC，物理地址默认只支持1MB空间。
开启A20可以取消这种模式，开启代码如下：
```
seta20.1:
    inb $0x64, %al                                  # Wait for not busy(8042 input buffer empty).
    testb $0x2, %al
    jnz seta20.1
    movb $0xd1, %al                                 # 0xd1 -> port 0x64
    outb %al, $0x64                                 # 0xd1 means: write data to 8042's P2 port

seta20.2:
    inb $0x64, %al                                  # Wait for not busy(8042 input buffer empty).
    testb $0x2, %al
    jnz seta20.2
    movb $0xdf, %al                                 # 0xdf -> port 0x60
    outb %al, $0x60                                 # 0xdf = 11011111, means set P2's A20 bit(the 1 bit) to 1
```

A20位于8042键盘控制器状态位上。由于尚未开启中断，用轮询方式等待键盘控制器空闲。
首先发出写8042输出端的指令，然后置A20为1。

初始化GDT表：
```
lgdt gdtdesc
```
通过lgdt指令加载已有的gdt表。

进入保护模式：
```
movl %cr0, %eax
orl $CR0_PE_ON, %eax
movl %eax, %cr0
```

将cr0寄存器PE位置1，就进入了保护模式。

##练习4：分析bootloader加载ELF格式的OS的过程。

###bootloader如何读取硬盘扇区

bootmain.c中的readsect函数实现了读取第secno扇区数据到dst，所有的IO操作是通过CPU访问硬盘的IO地址寄存器完成。

流程为：等待磁盘准备好->发出读取扇区的命令->等待磁盘准备好->把磁盘扇区数据读到指定内存

readseg函数调用readsect，实现了从offset开始读取count字节到虚地址va。

###bootloader如何加载ELF格式的OS

通过bootmain函数加载elf格式的OS。

首先读取elf文件的header，通过e_magic判断elf文件是否合法。

header中描述了elf文件加载的位置，按照描述把elf文件中的数据载入内存。

最后按header描述找到内核入口。

##练习5：实现函数调用堆栈跟踪函数

在kdebug.c中实现函数print_stackframe。

首先调用read_ebp，read_eip读取当前ebp、eip的值，于地址(unit32_t)ebp+2处获得参数，输出debug_info。

然后获得上一级调用函数的eip=ss:[ebp+4]，ebp=ss:[ebp]，可逐层输出函数调用栈的信息。

运行make qemu后结果如下：

```
ebp:0x00007b08 eip:0x001009a6 args:0x00010094 0x00000000 0x00007b38 0x00100092     kern/debug/kdebug.c:308: print_stackframe+21
ebp:0x00007b18 eip:0x00100c95 args:0x00000000 0x00000000 0x00000000 0x00007b88     kern/debug/kmonitor.c:125: mon_backtrace+10
ebp:0x00007b38 eip:0x00100092 args:0x00000000 0x00007b60 0xffff0000 0x00007b64     kern/init/init.c:48: grade_backtrace2+33
ebp:0x00007b58 eip:0x001000bb args:0x00000000 0xffff0000 0x00007b84 0x00000029     kern/init/init.c:53: grade_backtrace1+38
ebp:0x00007b78 eip:0x001000d9 args:0x00000000 0x00100000 0xffff0000 0x0000001d     kern/init/init.c:58: grade_backtrace0+23
ebp:0x00007b98 eip:0x001000fe args:0x0010347c 0x00103460 0x0000132a 0x00000000     kern/init/init.c:63: grade_backtrace+34
ebp:0x00007bc8 eip:0x00100055 args:0x00000000 0x00000000 0x00000000 0x00010094     kern/init/init.c:28: kern_init+84
ebp:0x00007bf8 eip:0x00007d68 args:0xc031fcfa 0xc08ed88e 0x64e4d08e 0xfa7502a8     <unknow>: -- 0x00007d67 --
```
与要求输出一致。

其中，最后一行对应第一个使用堆栈的bootmain函数，堆栈设置从0x7c00开始，call指令压栈后，ebp为0x7bf8。

与答案相比基本一致，在指针操作处理上略有不同。

##练习6：完善中断初始化和处理


###[6-1]中断描述符表（也可简称为保护模式下的中断向量表）中一个表项占多少字节？其中哪几位代表中断处理代码的入口？

一个表项占8字节，2~3字节为段选择子，0~1,6~7字节为段内偏移，两者结合表示中断处理代码入口。

###[6-2]请编程完善kern/trap/trap.c中对中断向量表进行初始化的函数idt_init。在idt_init函数中，依次对所有中断入口进行初始化。使用mmu.h中的SETGATE宏，填充idt数组内容。每个中断的入口由tools/vectors.c生成，使用trap.c中声明的vectors数组即可。

遍历整个idt数组，用SETGATE宏初始化，使用特权级(DPL)为0的中断门描述符，权限为内核态权限。

然后修改系统调用中断(T_SYSCALL)，使用陷阱门描述符且权限为用户态权限。

最后用lidt加载idt。

与参考答案相比，多了修改系统调用权限为用户态这一操作。

###[6-3]请编程完善trap.c中的中断处理函数trap，在对时钟中断进行处理的部分填写trap函数中处理时钟中断的部分，使操作系统每遇到100次时钟中断后，调用print_ticks子程序，向屏幕上打印一行文字”100 ticks”。

设置全局变量ticknum，记录时钟中断次数。

trap_dispatch函数中，每遇到1次时钟中断，ticknum自加1，到达100次时调用print_ticks函数。

实现与参考答案基本一致。

##本实验中重要的知识点
###生成操作系统镜像文件的过程
不属于OS原理的重点，在讲解系统启动过程时会提到。实验中阅读Makefile每一步生成过程，是和原理讲解不同的切入点。
###bootloader启动过程
在OS原理和实验中都很注重这个知识点。通过单步跟踪能熟悉系统的启动流程。
###实模式与保护模式的切换
OS原理主要讲解两种模式的差异，实验更注重模式切换的过程，包括开启A20，加载gdt表，更改cr0寄存器等。通过实验对其实施细节更进一步了解了。
###函数调用栈
这个知识点在汇编课上已经学到，比较熟悉，实验主要应用了通过ebp寄存器找到上一级调用者地址。
###中断处理
实验中未完成拓展练习，只做了简单的时钟中断处理。在lab1中没有体现出中断处理的复杂流程。

##我认为OS原理中很重要，但在实验中没有对应上的知识点
###中断的优先级和屏蔽
