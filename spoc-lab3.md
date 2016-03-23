## v9-cpu相关
---
(1)分析并编译运行v9-cpu git repo的testing branch中的,root/etc/os_lab2.c os_lab3.c os_lab3_1.c,理解虚存机制是如何在v9-cpu上实现的，思考如何实现clock页替换算法，并给出你的概要设计方案。

观察os\_lab3\_1.c中trap函数对缺页异常的处理。

```
if(mem_maps_num>=UPHYSZ/PAGE) { //need swap out
				    pa=swap_out(init->pdir);
				    printf("swap out a page\n");	
				    mappage(init->pdir, va & -PAGE, pa  & -PAGE, PTE_P | PTE_W | PTE_U);
			     } else {
				    printf("ADD new phy page\n");	
				    mappage(init->pdir, va & -PAGE, V2P+(memset(kalloc(), 0, PAGE)), PTE_P | PTE_W | PTE_U);
			     }
```

可知在物理内存足够时调用kalloc分配新页，不足时将调用swap_out函数换出一页。

为实现clock算法，需要修改以上两个函数。

用环形链表组织页，指针指向初始位置。

在kalloc函数中，装入新的一页时，访问位初始化为0。

访问页面时访问位置1。

在swap_out函数中，