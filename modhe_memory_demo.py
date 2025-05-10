#!/usr/bin/env python3
"""
使用ModHE进行内存跟踪的演示
"""
import sys
import math
from MemoryTracker import CacheStyle, MemoryTracker
from MemoryConfig import MemoryConfig, SimulationRunner
import ModHE

def demo_simple_operation():
    """演示简单的内存跟踪"""
    print("演示: 简单内存跟踪")
    print("-" * 50)
    
    # 创建ASIC
    asic = ModHE.ASIC(0)
    
    # 参数
    N = 2**16
    E = 1024
    l = 16
    R = 8
    r = 2
    
    # 创建内存跟踪器
    tracker = MemoryTracker(asic, CacheStyle.ALPHA, 16 * 1024 * 1024)  # 16MB缓存
    tracker.dnum = 2  # 设置dnum参数
    
    # 使用内存跟踪运行操作
    print("使用内存跟踪运行乘法操作...")
    result = tracker.multiply_with_memory(N, E, l, R, r)
    
    # 计算DRAM传输延迟
    dram_latency_cycles = tracker.calculate_dram_latency()
    compute_cycles = result * asic.F  # 转换为周期数
    total_cycles = compute_cycles + dram_latency_cycles
    
    # 打印内存统计
    stats = tracker.get_memory_stats()
    print(f"\n计算时间: {compute_cycles:.2f} 周期")
    print(f"DRAM延迟: {dram_latency_cycles:.2f} 周期")
    print(f"总操作时间: {total_cycles:.2f} 周期")
    print(f"DRAM读取: {stats.dram_limb_rd / (1024**2):.2f} MB")
    print(f"DRAM写入: {stats.dram_limb_wr / (1024**2):.2f} MB")
    print(f"密钥读取: {stats.dram_key_rd / (1024**2):.2f} MB")
    print(f"总传输量: {stats.total_dram_transfers / (1024**2):.2f} MB")
    
    # 计算缓存效率
    cache_efficiency = 0
    if stats.max_cache_size > 0:
        cache_mb = min(stats.max_cache_usage / (1024**2), 16)
        cache_efficiency = cache_mb / 16 * 100
    print(f"最大缓存使用: {cache_mb:.2f} MB")
    print(f"缓存效率: {cache_efficiency:.2f}%")
    
    # 与原始操作比较
    print("\n运行不带跟踪的操作进行比较...")
    original_result = asic.multiply(N, E, l, R, r)
    print(f"原始时间: {original_result:.2f} 周期")

def demo_cache_comparison():
    """演示比较不同的缓存风格"""
    print("\n演示: 缓存风格比较")
    print("-" * 50)
    
    # 创建模拟运行器
    runner = SimulationRunner()
    
    # 参数
    N = 2**16
    E = 1024
    l = 16
    R = 8
    r = 2
    
    # 设置dnum参数
    runner.dnum = 2
    
    # 定义缓存配置
    cache_configs = [
        MemoryConfig(cache_style=CacheStyle.NONE, max_cache_size_mb=0),
        MemoryConfig(cache_style=CacheStyle.CONST, max_cache_size_mb=1),
        MemoryConfig(cache_style=CacheStyle.BETA, max_cache_size_mb=4),
        MemoryConfig(cache_style=CacheStyle.ALPHA, max_cache_size_mb=16),
        MemoryConfig(cache_style=CacheStyle.HUGE, max_cache_size_mb=250)
    ]
    
    # 比较缓存风格
    print(f"{'缓存风格':<15}{'总时间 (周期)':<15}{'计算时间 (周期)':<18}{'DRAM延迟 (周期)':<18}{'DRAM传输 (MB)':<15}{'缓存使用 (MB)':<15}{'缓存效率 (%)':<15}")
    print("-" * 120)
    
    for config in cache_configs:
        runner.configure(config)
        result = runner.run_benchmark("multiply", N, E, l, R, r)
        stats = result["memory_stats"]
        
        # 计算缓存效率
        if config.max_cache_size_mb > 0:
            # 对于NONE风格，缓存效率应该为0
            if config.cache_style == CacheStyle.NONE:
                cache_mb = 0.0
                efficiency = 0.0
            else:
                # 限制最大缓存使用不超过配置的大小
                cache_mb = min(stats.max_cache_usage / (1024**2), config.max_cache_size_mb)
                efficiency = cache_mb / config.max_cache_size_mb * 100
        else:
            cache_mb = 0.0
            efficiency = 0.0
            
        print(f"{config.cache_style.name:<15}{result['time']:<15.2f}"
              f"{result['compute_time']:<18.2f}{result['dram_latency']:<18.2f}"
              f"{stats.total_dram_transfers / (1024**2):<15.2f}"
              f"{cache_mb:<15.2f}"
              f"{efficiency:<15.2f}")

def demo_keyswitching():
    """演示密钥切换操作"""
    print("\n演示: 密钥切换操作")
    print("-" * 50)
    
    # 创建模拟运行器
    runner = SimulationRunner()
    
    # 参数
    N = 2**16
    E = 1024
    l = 16
    R = 8
    r = 2
    
    # 设置dnum参数
    runner.dnum = 2
    
    # 配置大缓存
    config = MemoryConfig(cache_style=CacheStyle.HUGE, max_cache_size_mb=250)
    runner.configure(config)
    
    # 运行密钥切换基准测试
    print("使用大缓存运行密钥切换...")
    result = runner.run_benchmark("keyswitch", N, E, l, R, r)
    stats = result["memory_stats"]
    
    # 计算缓存效率
    cache_mb = min(stats.max_cache_usage / (1024**2), 250)
    efficiency = cache_mb / 250 * 100
    
    print(f"\n总时间: {result['time']:.2f} 周期")
    print(f"计算时间: {result['compute_time']:.2f} 周期")
    print(f"DRAM延迟: {result['dram_latency']:.2f} 周期")
    print(f"DRAM读取: {stats.dram_limb_rd / (1024**2):.2f} MB")
    print(f"DRAM写入: {stats.dram_limb_wr / (1024**2):.2f} MB")
    print(f"密钥读取: {stats.dram_key_rd / (1024**2):.2f} MB")
    print(f"总传输量: {stats.total_dram_transfers / (1024**2):.2f} MB")
    print(f"最大缓存使用: {cache_mb:.2f} MB")
    print(f"缓存效率: {efficiency:.2f}%")
    
    # 配置无缓存
    config = MemoryConfig(cache_style=CacheStyle.NONE, max_cache_size_mb=0)
    runner.configure(config)
    
    # 运行密钥切换基准测试
    print("\n使用无缓存运行密钥切换...")
    result = runner.run_benchmark("keyswitch", N, E, l, R, r)
    stats = result["memory_stats"]
    
    print(f"总时间: {result['time']:.2f} 周期")
    print(f"计算时间: {result['compute_time']:.2f} 周期")
    print(f"DRAM延迟: {result['dram_latency']:.2f} 周期")
    print(f"DRAM读取: {stats.dram_limb_rd / (1024**2):.2f} MB")
    print(f"DRAM写入: {stats.dram_limb_wr / (1024**2):.2f} MB")
    print(f"密钥读取: {stats.dram_key_rd / (1024**2):.2f} MB")
    print(f"总传输量: {stats.total_dram_transfers / (1024**2):.2f} MB")

def main():
    """运行所有演示"""
    print("ModHE内存模拟演示")
    print("==========================")
    
    demo_simple_operation()
    demo_cache_comparison()
    demo_keyswitching()
    
    print("\n演示成功完成！")

if __name__ == "__main__":
    main()