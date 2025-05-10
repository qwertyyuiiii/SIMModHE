#!/usr/bin/env python3
"""
ModHE内存模拟的基准测试脚本
"""
import sys
import math
from datetime import datetime
from MemoryTracker import CacheStyle, MemoryTracker
from MemoryConfig import MemoryConfig, SimulationRunner

def format_bytes(size_bytes):
    """将字节格式化为人类可读的大小"""
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

def print_divider():
    """打印分隔线"""
    print("-" * 80)

def print_header(title):
    """打印章节标题"""
    print_divider()
    print(f" {title} ".center(80, "="))
    print_divider()

def run_operation_benchmarks(runner, config, operation, N, E, l_values, R, r):
    """对不同的l值运行基准测试"""
    print_header(f"使用{config.cache_style.name}缓存对{operation}进行基准测试")
    print(f"缓存大小: {format_bytes(config.max_cache_bytes)}")
    print(f"参数: N={N}, E={E}, R={R}, r={r}")
    print_divider()
    
    print(f"{'Limbs (l)':<10}{'时间 (周期)':<15}{'DRAM读取':<20}{'DRAM写入':<20}{'总传输量':<20}")
    print_divider()
    
    runner.configure(config)
    
    for l in l_values:
        result = runner.run_benchmark(operation, N, E, l, R, r)
        stats = result["memory_stats"]
        
        print(f"{l:<10}{result['time']:<15.2f}{format_bytes(stats.dram_limb_rd):<20}"
              f"{format_bytes(stats.dram_limb_wr):<20}{format_bytes(stats.total_dram_transfers):<20}")
    
    print_divider()

def compare_cache_styles(N=2**16, E=1024, l=16, R=8, r=2):
    """比较不同缓存风格的操作"""
    print_header("缓存风格比较")
    
    runner = SimulationRunner()
    runner.dnum = 2  # 设置dnum参数
    
    cache_configs = [
        MemoryConfig(cache_style=CacheStyle.NONE, max_cache_size_mb=0),
        MemoryConfig(cache_style=CacheStyle.CONST, max_cache_size_mb=1),
        MemoryConfig(cache_style=CacheStyle.BETA, max_cache_size_mb=4),
        MemoryConfig(cache_style=CacheStyle.ALPHA, max_cache_size_mb=16),
        MemoryConfig(cache_style=CacheStyle.HUGE, max_cache_size_mb=250)
    ]
    
    operations = ["multiply", "rotate", "keyswitch"]
    
    for operation in operations:
        print_header(f"{operation.upper()} - 缓存风格比较")
        print(f"{'缓存风格':<15}{'时间 (周期)':<15}{'DRAM传输':<20}{'最大缓存使用':<20}")
        print_divider()
        
        for config in cache_configs:
            runner.configure(config)
            result = runner.run_benchmark(operation, N, E, l, R, r)
            stats = result["memory_stats"]
            
            print(f"{config.cache_style.name:<15}{result['time']:<15.2f}"
                  f"{format_bytes(stats.total_dram_transfers):<20}"
                  f"{format_bytes(stats.max_cache_usage):<20}")
        
        print_divider()
        print()
        
        # 缓存行为分析
        print("缓存行为分析:")
        
        # 详细性能指标比较
        print("性能指标比较:")
        print(f"{'缓存风格':<10}{'总时间 (周期)':<15}{'计算时间 (周期)':<18}{'内存时间 (周期)':<18}{'DRAM传输 (MB)':<15}{'缓存命中率':<15}")
        print("-" * 100)
        
        # 为每个测试单独配置和运行基准测试，以获得独立的统计数据
        runner.configure(MemoryConfig(cache_style=CacheStyle.NONE, max_cache_size_mb=0))
        result_none = runner.run_benchmark(operation, N, E, l, R, r, reset_stats=True)
        stats_none = result_none["memory_stats"]
        print(f"NONE{'':<6}{result_none['time']:<15.2f}{result_none['compute_time']:<18.2f}{result_none['memory_time']:<18.2f}{stats_none.total_dram_transfers / (1024**2):<15.2f}{'N/A':<15}")
        
        runner.configure(MemoryConfig(cache_style=CacheStyle.CONST, max_cache_size_mb=1))
        result_const = runner.run_benchmark(operation, N, E, l, R, r, reset_stats=True)
        stats_const = result_const["memory_stats"]
        print(f"CONST{'':<5}{result_const['time']:<15.2f}{result_const['compute_time']:<18.2f}{result_const['memory_time']:<18.2f}{stats_const.total_dram_transfers / (1024**2):<15.2f}{result_const['cache_hit_rate']*100:<15.2f}%")
        
        runner.configure(MemoryConfig(cache_style=CacheStyle.BETA, max_cache_size_mb=4))
        result_beta = runner.run_benchmark(operation, N, E, l, R, r, reset_stats=True)
        stats_beta = result_beta["memory_stats"]
        print(f"BETA{'':<6}{result_beta['time']:<15.2f}{result_beta['compute_time']:<18.2f}{result_beta['memory_time']:<18.2f}{stats_beta.total_dram_transfers / (1024**2):<15.2f}{result_beta['cache_hit_rate']*100:<15.2f}%")
        
        runner.configure(MemoryConfig(cache_style=CacheStyle.ALPHA, max_cache_size_mb=16))
        result_alpha = runner.run_benchmark(operation, N, E, l, R, r, reset_stats=True)
        stats_alpha = result_alpha["memory_stats"]
        print(f"ALPHA{'':<5}{result_alpha['time']:<15.2f}{result_alpha['compute_time']:<18.2f}{result_alpha['memory_time']:<18.2f}{stats_alpha.total_dram_transfers / (1024**2):<15.2f}{result_alpha['cache_hit_rate']*100:<15.2f}%")
        
        runner.configure(MemoryConfig(cache_style=CacheStyle.HUGE, max_cache_size_mb=250))
        result_huge = runner.run_benchmark(operation, N, E, l, R, r, reset_stats=True)
        stats_huge = result_huge["memory_stats"]
        print(f"HUGE{'':<6}{result_huge['time']:<15.2f}{result_huge['compute_time']:<18.2f}{result_huge['memory_time']:<18.2f}{stats_huge.total_dram_transfers / (1024**2):<15.2f}{result_huge['cache_hit_rate']*100:<15.2f}%")
        
        print()
        
        # 计算DRAM传输减少百分比
        print("DRAM传输减少百分比:")
        none_transfers = stats_none.total_dram_transfers
        const_transfers = stats_const.total_dram_transfers
        beta_transfers = stats_beta.total_dram_transfers
        alpha_transfers = stats_alpha.total_dram_transfers
        huge_transfers = stats_huge.total_dram_transfers
        
        # 确保没有除以零，并处理负百分比情况
        if none_transfers > 0:
            none_const_reduction = (none_transfers - const_transfers) / none_transfers * 100
            print(f"  NONE -> CONST: DRAM传输减少 {none_const_reduction:.2f}%")
        else:
            print(f"  NONE -> CONST: 无法计算 (无DRAM传输)")
            
        if const_transfers > 0:
            const_beta_reduction = (const_transfers - beta_transfers) / const_transfers * 100
            print(f"  CONST -> BETA: DRAM传输减少 {const_beta_reduction:.2f}%")
        else:
            print(f"  CONST -> BETA: 无法计算 (无DRAM传输)")
            
        if beta_transfers > 0:
            beta_alpha_reduction = (beta_transfers - alpha_transfers) / beta_transfers * 100
            print(f"  BETA -> ALPHA: DRAM传输减少 {beta_alpha_reduction:.2f}%")
        else:
            print(f"  BETA -> ALPHA: 无法计算 (无DRAM传输)")
            
        if alpha_transfers > 0:
            alpha_huge_reduction = (alpha_transfers - huge_transfers) / alpha_transfers * 100
            print(f"  ALPHA -> HUGE: DRAM传输减少 {alpha_huge_reduction:.2f}%")
        else:
            print(f"  ALPHA -> HUGE: 无法计算 (无DRAM传输)")
            
        print()
        
        # 缓存使用效率
        print("缓存使用效率:")
        # 对于CONST
        if config.cache_style != CacheStyle.NONE and stats_const.max_cache_size > 0:
            const_cache_mb = min(stats_const.max_cache_usage / (1024**2), 1.0)
            const_efficiency = const_cache_mb / 1.0 * 100
            print(f"  CONST: {const_cache_mb:.2f}MB/{1}MB = {const_efficiency:.2f}%")
        
        # 对于BETA
        if config.cache_style != CacheStyle.NONE and stats_beta.max_cache_size > 0:
            beta_cache_mb = min(stats_beta.max_cache_usage / (1024**2), 4.0)
            beta_efficiency = beta_cache_mb / 4.0 * 100
            print(f"  BETA:  {beta_cache_mb:.2f}MB/{4}MB = {beta_efficiency:.2f}%")
        
        # 对于ALPHA
        if config.cache_style != CacheStyle.NONE and stats_alpha.max_cache_size > 0:
            alpha_cache_mb = min(stats_alpha.max_cache_usage / (1024**2), 16.0)
            alpha_efficiency = alpha_cache_mb / 16.0 * 100
            print(f"  ALPHA: {alpha_cache_mb:.2f}MB/{16}MB = {alpha_efficiency:.2f}%")
        
        # 对于HUGE
        if config.cache_style != CacheStyle.NONE and stats_huge.max_cache_size > 0:
            huge_cache_mb = min(stats_huge.max_cache_usage / (1024**2), 250.0)
            huge_efficiency = huge_cache_mb / 250.0 * 100
            print(f"  HUGE:  {huge_cache_mb:.2f}MB/{250}MB = {huge_efficiency:.2f}%")
            
        print_divider()

def main():
    """主基准测试函数"""
    print_header("ModHE内存模拟基准测试")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 默认参数
    N = 2**16     # 多项式度，使用更小的值以加快测试
    E = 1024     # ModHE中的值
    R = 8        # ModHE中的PE_R值
    r = 2        # 默认r值
    
    # 创建模拟运行器
    runner = SimulationRunner()
    
    # 设置dnum参数
    runner.dnum = 2
    
    # 使用不同的l值（limbs数量）进行基准测试
    l_values = [8, 12, 16, 20, 24]
    
    # 运行不同缓存风格的基准测试
    cache_configs = [
        MemoryConfig(cache_style=CacheStyle.NONE, max_cache_size_mb=0),
        MemoryConfig(cache_style=CacheStyle.ALPHA, max_cache_size_mb=16),
        MemoryConfig(cache_style=CacheStyle.HUGE, max_cache_size_mb=250)
    ]
    
    # 对乘法操作运行基准测试
    for config in cache_configs:
        run_operation_benchmarks(runner, config, "multiply", N, E, l_values, R, r)
    
    # 比较所有缓存风格
    compare_cache_styles()
    
    # 能量报告
    print_header("能量报告")
    NTT_Energy, MM_Energy, MA_Energy, Auto_Energy, total = runner.get_energy_report()
    print(f"NTT能量:  {NTT_Energy:.2f}")
    print(f"MM能量:   {MM_Energy:.2f}")
    print(f"MA能量:   {MA_Energy:.2f}")
    print(f"Auto能量: {Auto_Energy:.2f}")
    print(f"总能量: {total:.2f}")
    
    print_header("基准测试完成")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()