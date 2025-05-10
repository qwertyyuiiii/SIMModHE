import math
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from collections import OrderedDict
import ModHE  # 导入原始ModHE模块

class CacheStyle(Enum):
    """类似SimFHE的缓存风格"""
    NONE = 0     # 无缓存，所有操作都需要DRAM访问
    CONST = 1    # 常数小缓存（2-3个limbs）
    BETA = 2     # 用于β操作的缓存（dnum大小）
    ALPHA = 3    # 用于α操作的缓存（ceil(L/dnum)大小）
    HUGE = 4     # 可以容纳密钥的大缓存（250MB+）

@dataclass
class MemoryStats:
    """跟踪内存统计信息"""
    dram_limb_rd: int = 0        # DRAM limb读取（字节）
    dram_limb_wr: int = 0        # DRAM limb写入（字节）
    dram_key_rd: int = 0         # DRAM密钥读取（字节）
    dram_plain_rd: int = 0       # DRAM明文读取（字节）
    current_cache_size: int = 0  # 当前缓存使用量（字节）
    max_cache_usage: int = 0     # 最大缓存使用量（字节）
    max_cache_size: int = 0      # 最大缓存容量（字节）
    cache_style: CacheStyle = CacheStyle.NONE  # 缓存风格
    
    # 缓存性能统计
    cache_hits: int = 0          # 缓存命中次数
    cache_misses: int = 0        # 缓存未命中次数
    total_accesses: int = 0      # 总访问次数
    
    # 延迟统计（周期数）
    computation_cycles: int = 0  # 计算周期数
    memory_cycles: int = 0       # 内存访问周期数
    
    memory_transactions: List[Tuple[str, int]] = field(default_factory=list)
    
    @property
    def total_dram_transfers(self):
        """总DRAM传输量（字节）"""
        return self.dram_limb_rd + self.dram_limb_wr + self.dram_key_rd + self.dram_plain_rd
    
    @property
    def cache_hit_rate(self):
        """计算缓存命中率"""
        if self.total_accesses == 0:
            return 0
        return self.cache_hits / self.total_accesses
    
    def record_transaction(self, operation: str, size: int):
        """记录内存事务"""
        self.memory_transactions.append((operation, size))
    
    def __str__(self):
        """用于调试的字符串表示"""
        return (
            f"DRAM Limb读取: {self.dram_limb_rd / (1024**2):.2f} MB\n"
            f"DRAM Limb写入: {self.dram_limb_wr / (1024**2):.2f} MB\n"
            f"DRAM密钥读取: {self.dram_key_rd / (1024**2):.2f} MB\n"
            f"DRAM明文读取: {self.dram_plain_rd / (1024**2):.2f} MB\n"
            f"总DRAM传输: {self.total_dram_transfers / (1024**2):.2f} MB\n"
            f"最大缓存使用: {self.max_cache_usage / (1024**2):.2f} MB\n"
            f"缓存命中率: {self.cache_hit_rate * 100:.2f}%\n"
            f"计算周期: {self.computation_cycles}\n"
            f"内存周期: {self.memory_cycles}"
        )

class CacheLine:
    """模拟缓存行"""
    def __init__(self, address: str, size: int):
        self.address = address    # 缓存行地址标识符
        self.size = size          # 缓存行大小（字节）
        self.last_accessed = 0    # 最后访问时间戳
        self.dirty = False        # 是否被修改过
        
    def access(self, timestamp: int):
        """访问缓存行并更新时间戳"""
        self.last_accessed = timestamp
        
    def mark_dirty(self):
        """标记缓存行为脏"""
        self.dirty = True
        
    def clear_dirty(self):
        """清除脏标记"""
        self.dirty = False
        
    def is_dirty(self) -> bool:
        """检查缓存行是否为脏"""
        return self.dirty

class Cache:
    """实现模拟缓存"""
    def __init__(self, max_size: int, line_size: int = 4096):
        self.max_size = max_size          # 最大缓存大小（字节）
        self.line_size = line_size        # 缓存行大小（字节）
        self.current_size = 0             # 当前使用的缓存大小
        self.timestamp = 0                # 当前时间戳
        self.lines = OrderedDict()        # 缓存行映射 {地址: CacheLine}
        self.prefetch_candidates = set()  # 预取候选地址
        self.burst_size = 64              # 突发传输大小（字节）
        
    def get_timestamp(self) -> int:
        """获取并递增时间戳"""
        self.timestamp += 1
        return self.timestamp
        
    def lookup(self, address: str, size: int) -> bool:
        """查找地址是否在缓存中"""
        return address in self.lines
    
    def get_line_address(self, address: str) -> str:
        """获取地址对应的缓存行地址"""
        # 实际实现可能更复杂，这里简化处理
        return address
    
    def evict(self, needed_size: int) -> int:
        """驱逐缓存行以腾出空间
        
        返回:
            写回DRAM的字节数
        """
        bytes_written = 0
        
        # 如果不需要腾出空间，直接返回
        if self.current_size + needed_size <= self.max_size:
            return bytes_written
            
        # 根据LRU策略腾出空间
        while self.current_size + needed_size > self.max_size and self.lines:
            # 获取最早访问的缓存行地址
            oldest_addr = next(iter(self.lines))
            oldest_line = self.lines[oldest_addr]
            
            # 如果缓存行为脏，需要写回DRAM
            if oldest_line.is_dirty():
                bytes_written += oldest_line.size
                
            # 从缓存中移除该行
            self.current_size -= oldest_line.size
            del self.lines[oldest_addr]
            
        return bytes_written
    
    def access(self, address: str, size: int, is_write: bool = False) -> Tuple[bool, int]:
        """访问缓存
        
        参数:
            address: 访问的地址
            size: 访问的数据大小（字节）
            is_write: 是否为写操作
            
        返回:
            (命中与否, DRAM传输字节数)
        """
        if self.max_size == 0:  # 如果没有缓存
            return False, size
            
        line_addr = self.get_line_address(address)
        timestamp = self.get_timestamp()
        
        # 检查缓存命中
        if line_addr in self.lines:
            # 缓存命中
            cache_line = self.lines[line_addr]
            
            # 更新访问时间戳，将此行移到LRU队列末尾
            cache_line.access(timestamp)
            self.lines.move_to_end(line_addr)
            
            # 如果是写操作，标记为脏
            if is_write:
                cache_line.mark_dirty()
                
            # 添加相邻地址到预取候选集
            self.add_prefetch_candidates(address)
                
            return True, 0
        
        # 缓存未命中
        # 计算需要从DRAM读取的数据量（按突发大小对齐）
        transfer_size = math.ceil(size / self.burst_size) * self.burst_size
        
        # 驱逐缓存行以腾出空间
        bytes_written = self.evict(size)
        
        # 创建新的缓存行
        new_line = CacheLine(line_addr, size)
        if is_write:
            new_line.mark_dirty()
        new_line.access(timestamp)
        
        # 将新行添加到缓存
        self.lines[line_addr] = new_line
        self.current_size += size
        
        # 添加相邻地址到预取候选集
        self.add_prefetch_candidates(address)
        
        # 尝试预取数据
        prefetch_bytes = self.prefetch()
        
        return False, transfer_size + bytes_written + prefetch_bytes
    
    def add_prefetch_candidates(self, address: str):
        """添加预取候选地址"""
        # 在实际实现中可能会基于访问模式添加相邻地址
        # 这里简化处理
        pass
        
    def prefetch(self) -> int:
        """执行预取操作，返回预取的字节数"""
        # 简化的预取实现
        prefetch_bytes = 0
        candidates_to_remove = set()
        
        for addr in self.prefetch_candidates:
            if addr not in self.lines and self.current_size + self.line_size <= self.max_size:
                # 预取此地址
                self.lines[addr] = CacheLine(addr, self.line_size)
                self.current_size += self.line_size
                prefetch_bytes += self.line_size
                candidates_to_remove.add(addr)
                
        # 移除已预取的候选地址
        self.prefetch_candidates -= candidates_to_remove
        
        return prefetch_bytes
    
    def flush(self) -> int:
        """刷新所有脏缓存行，返回写回DRAM的字节数"""
        bytes_written = 0
        lines_to_clear = []
        
        for addr, line in self.lines.items():
            if line.is_dirty():
                bytes_written += line.size
                lines_to_clear.append(addr)
                
        # 清除脏标记
        for addr in lines_to_clear:
            self.lines[addr].clear_dirty()
            
        return bytes_written
    
    def clear(self):
        """清空缓存"""
        bytes_written = self.flush()
        self.lines.clear()
        self.current_size = 0
        self.prefetch_candidates.clear()
        return bytes_written

class MemoryTracker:
    """ModHE的内存跟踪器"""
    def __init__(self, asic: ModHE.ASIC, cache_style: CacheStyle = CacheStyle.NONE, max_cache_size: int = 0):
        self.asic = asic
        self.cache_style = cache_style
        self.max_cache_size = max_cache_size  # 最大缓存大小（字节）
        
        # 创建缓存对象
        self.cache = Cache(max_cache_size)
        
        # 创建统计对象
        self.stats = MemoryStats(max_cache_size=max_cache_size, cache_style=cache_style)
        
        # 根据ASIC参数计算关键属性
        self.N = 1 << asic.m_bits  # 多项式度
        self.logq = 50  # 默认使用50位
        self.PE_R = asic.PE_R      # PE阵列维度
        self.bandwidth = asic.BD * 10**9 / 8  # 将Gb/s转换为Bytes/s
        self.frequency = asic.F    # 芯片频率（Hz）
        
        # 内存访问延迟模型参数
        self.dram_base_latency = 45    # DRAM基本访问延迟（周期）
        self.cache_hit_latency = 2     # 缓存命中延迟（周期）
        self.burst_size = 64           # HBM突发传输大小（字节）
        self.max_concurrency = 8       # 最大并发请求数
        
        # 跟踪当前缓存中的数据
        self.cached_data = {}  # 格式: {数据标识: 大小}
        self.dnum = 2  # 默认dnum参数
        
        # 将操作的时间存储在ASIC对象中
        self.asic.multiplytime = 0
        self.asic.Rotatetime = 0
        
    def calculate_size_in_bytes(self, N: int, limbs: int) -> int:
        """根据N和limb数量计算字节大小"""
        size = int(math.ceil((N * limbs * self.logq) / 8))
        return max(size, 1024)
    
    def memory_access(self, address: str, size: int, is_write: bool = False) -> int:
        """模拟内存访问，返回访问延迟
        """
        # 更新访问统计
        self.stats.total_accesses += 1
        
        # 检查缓存命中
        hit, dram_bytes = self.cache.access(address, size, is_write)
        
        if hit:
            # 缓存命中
            self.stats.cache_hits += 1
            latency = self.cache_hit_latency
        else:
            # 缓存未命中
            self.stats.cache_misses += 1
            
            # 计算DRAM访问延迟
            latency = self.calculate_dram_access_latency(dram_bytes)
            
            if is_write:
                self.stats.dram_limb_wr += dram_bytes
            else:
                self.stats.dram_limb_rd += dram_bytes
        
        # 更新内存周期统计
        self.stats.memory_cycles += latency
        
        return latency
    
    def calculate_dram_access_latency(self, bytes_transferred: int) -> int:
        """计算DRAM访问延迟（周期）"""
        if bytes_transferred == 0:
            return 0
            
        # 计算请求数
        requests = math.ceil(bytes_transferred / self.burst_size)
        
        # 计算批次数（考虑并行性）
        batches = math.ceil(requests / self.max_concurrency)
        
        # 计算传输周期数
        bytes_per_cycle = self.bandwidth / self.frequency
        transfer_cycles = bytes_transferred / bytes_per_cycle
        
        # 小于1MB的传输，延迟主导；大于1MB的传输，带宽主导
        if bytes_transferred < 1024 * 1024:
            # 前几个请求受延迟影响较大，后续请求可以并行处理
            latency = self.dram_base_latency + (batches - 1) * 5 + transfer_cycles * 0.2
        else:
            # 大数据量主要受带宽限制，但可以通过并行优化减少部分延迟
            latency = self.dram_base_latency + transfer_cycles * 0.6
        
        return int(latency)
    
    def read_limb(self, N: int, limbs: int):
        """模拟从DRAM读取limbs"""
        size = self.calculate_size_in_bytes(N, limbs)
        address = f"limb_{N}_{limbs}_{id(self)}"
        
        # 记录读取事务
        self.stats.record_transaction("read_limb", size)
        
        # 如果是NONE缓存风格，直接从DRAM读取
        if self.cache_style == CacheStyle.NONE:
            self.stats.dram_limb_rd += size
            latency = self.calculate_dram_access_latency(size)
            self.stats.memory_cycles += latency
            return size
        
        # 其他缓存风格，尝试从缓存读取
        latency = self.memory_access(address, size, False)
        
        # 更新最大缓存使用量统计
        if self.cache.current_size > self.stats.max_cache_usage:
            self.stats.max_cache_usage = self.cache.current_size
        
        return size
    
    def write_limb(self, N: int, limbs: int):
        """模拟将limbs写入DRAM"""
        size = self.calculate_size_in_bytes(N, limbs)
        address = f"limb_{N}_{limbs}_{id(self)}"
        
        # 记录写入事务
        self.stats.record_transaction("write_limb", size)
        
        # 如果是NONE缓存风格，直接写入DRAM
        if self.cache_style == CacheStyle.NONE:
            self.stats.dram_limb_wr += size
            latency = self.calculate_dram_access_latency(size)
            self.stats.memory_cycles += latency
            return size
        
        # 其他缓存风格，尝试写入缓存
        latency = self.memory_access(address, size, True)
        
        # 更新最大缓存使用量统计
        if self.cache.current_size > self.stats.max_cache_usage:
            self.stats.max_cache_usage = self.cache.current_size
        
        return size
    
    def read_key(self, N: int, limbs: int, compressed: bool = True):
        """模拟从DRAM读取密钥"""
        size = self.calculate_size_in_bytes(N, limbs)
        if not compressed:
            size *= 2  # 未压缩的密钥大小是两倍
            
        address = f"key_{N}_{limbs}_{id(self)}"
        
        # 记录读取事务
        self.stats.record_transaction("read_key", size)
        
        # 密钥总是从DRAM读取
        self.stats.dram_key_rd += size
        latency = self.calculate_dram_access_latency(size)
        self.stats.memory_cycles += latency
        
        # 如果不是NONE模式，尝试缓存密钥
        if self.cache_style != CacheStyle.NONE and self.cache_style.value >= CacheStyle.HUGE.value:
            # 只有HUGE缓存才尝试缓存整个密钥
            hit, _ = self.cache.access(address, size, False)
            
            # 更新最大缓存使用量统计
            if self.cache.current_size > self.stats.max_cache_usage:
                self.stats.max_cache_usage = self.cache.current_size
        
        return size
    
    def read_plaintext(self, N: int, limbs: int):
        """模拟从DRAM读取明文"""
        size = self.calculate_size_in_bytes(N, limbs)
        address = f"plaintext_{N}_{limbs}_{id(self)}"
        
        # 记录读取事务
        self.stats.record_transaction("read_plaintext", size)
        
        # 明文总是从DRAM读取
        self.stats.dram_plain_rd += size
        latency = self.calculate_dram_access_latency(size)
        self.stats.memory_cycles += latency
        
        # 如果不是NONE模式，尝试缓存明文
        if self.cache_style != CacheStyle.NONE:
            hit, _ = self.cache.access(address, size, False)
            
            # 更新最大缓存使用量统计
            if self.cache.current_size > self.stats.max_cache_usage:
                self.stats.max_cache_usage = self.cache.current_size
        
        return size
    
    def release_cache(self, size: int):
        """模拟释放缓存空间        """
        pass
    
    def check_cache_available(self, size: int) -> bool:
        """检查缓存是否有可用空间"""
        if self.cache_style == CacheStyle.NONE or self.max_cache_size == 0:
            return False
        return self.cache.current_size + size <= self.max_cache_size

    def multiply_pe_with_memory(self, N, E, l, R, r, NUM=1, inner=1):
        """为multiply_pe添加内存跟踪"""
        # 读取输入
        if self.cache_style == CacheStyle.NONE:
            self.read_limb(N, l)
        else:
            # 对于有缓存的情况，尝试使用缓存
            self.read_limb(N, l)
        
        # 调用原始函数获取计算时间
        result = self.asic.multiply_pe(N, E, l, R, r, NUM, inner)
        
        # 更新计算周期统计
        computation_cycles = result * self.frequency
        self.stats.computation_cycles += computation_cycles
        
        # 如果缓存不够大，写出输出
        if self.cache_style == CacheStyle.NONE:
            self.write_limb(N, l)
        else:
            # 对于有缓存的情况，尝试使用缓存
            self.write_limb(N, l)
            
        return result

    def multiply_add_with_memory(self, N, E, l, R, r, NUM=1, inner=1):
        """为multiply_add添加内存跟踪"""
        # 读取输入
        if self.cache_style == CacheStyle.NONE:
            self.read_limb(N, l)
        else:
            # 对于有缓存的情况，尝试使用缓存
            self.read_limb(N, l)
        
        # 调用原始函数获取计算时间
        result = self.asic.multiply_add(N, E, l, R, r, NUM, inner)
        
        # 更新计算周期统计
        computation_cycles = result * self.frequency
        self.stats.computation_cycles += computation_cycles
        
        # 如果缓存不够大，写出输出
        if self.cache_style == CacheStyle.NONE:
            self.write_limb(N, l)
        else:
            # 对于有缓存的情况，尝试使用缓存
            self.write_limb(N, l)
            
        return result

    def add_plain_with_memory(self, N, E, l, R, r, NUM=1, inner=1):
        """为add_plain添加内存跟踪"""
        # 读取输入
        self.read_limb(N, l)  # 读取密文
        self.read_plaintext(N, 1)  # 读取明文
        
        # 调用原始函数获取计算时间
        result = self.asic.add_plain(N, E, l, R, r, NUM, inner)
        
        # 更新计算周期统计
        computation_cycles = result * self.frequency
        self.stats.computation_cycles += computation_cycles
        
        # 写出输出
        self.write_limb(N, l)
            
        return result

    def mod_up_with_memory(self, N, E, l, R, r, NUM=1, inner=1):
        """为mod_up添加内存跟踪"""
        # 读取输入
        self.read_limb(N, l)
        
        # 调用原始函数获取计算时间
        result = self.asic.mod_up(N, E, l, R, r, NUM, inner)
        
        # 更新计算周期统计
        computation_cycles = result * self.frequency
        self.stats.computation_cycles += computation_cycles
        
        # 写出输出
        self.write_limb(N, l + 1)  # 模数提升后增加一个limb
            
        return result

    def mod_down_with_memory(self, N, E, l, R, r, NUM=1, inner=1):
        """为mod_down添加内存跟踪"""
        # 读取输入
        self.read_limb(N, l)
        
        # 调用原始函数获取计算时间
        result = self.asic.mod_down(N, E, l, R, r, NUM, inner)
        
        # 更新计算周期统计
        computation_cycles = result * self.frequency
        self.stats.computation_cycles += computation_cycles
        
        # 写出输出
        self.write_limb(N, l - 1)  # 模数降低后减少一个limb
            
        return result

    def ntt_with_memory(self, N, E, l, R, r, NUM=1, inner=1):
        """为ntt添加内存跟踪"""
        # 读取输入
        self.read_limb(N, l)
        
        # 调用原始函数获取计算时间
        result = self.asic.ntt(N, E, l, R, r, NUM, inner)
        
        # 更新计算周期统计
        computation_cycles = result * self.frequency
        self.stats.computation_cycles += computation_cycles
        
        # 写出输出
        self.write_limb(N, l)
            
        return result

    def multiply_with_memory(self, N, E, l, R, r, NUM=1):
        """为multiply添加内存跟踪"""
        alpha = math.ceil(l / self.dnum)
        DNUM = l
        
        # 读取两个多项式（或从缓存中获取）
        self.read_limb(N, l * 2)
        
        # 跟踪multiply_pe的内存
        t1 = self.multiply_pe_with_memory(N, E, l, R, r, NUM)
        
        # 跟踪ntt的内存
        t2 = self.ntt_with_memory(N, E, l, R, r, NUM, inner=(r*(r+1)/2))
        
        # 跟踪mod_up的内存
        t3 = self.mod_up_with_memory(N, E, l, R, r, NUM, inner=DNUM*(r*(r+1)/2))
        
        # 跟踪ntt的内存
        t4 = self.ntt_with_memory(N, E, l, R, r, NUM, inner=DNUM*(r*(r+1)/2))
        
        # 跟踪multiply_add的内存
        t5 = self.multiply_add_with_memory(N, E, l, R, r, NUM*(r+1), inner=(r*(r+1)/2)*math.pow(4, R/r-1))*(DNUM+1)
        
        # 跟踪ntt的内存
        t6 = self.ntt_with_memory(N, E, 1, R, r, NUM*(l+1)*(r+1), inner=1)
        
        # 跟踪mod_down的内存
        t7 = self.mod_down_with_memory(N, E, l, R, r, NUM*(r+1), inner=1)
        
        # 跟踪ntt的内存
        t8 = self.ntt_with_memory(N, E, l, R, r, NUM*(r+1), inner=1)
        
        # 跟踪add_plain的内存
        t9 = self.add_plain_with_memory(N, E, l, R, r, NUM=NUM*(r+1))
        
        # 写出结果
        self.write_limb(N, l)
        
        # 调用原始函数获取正确的时间
        result = self.asic.multiply(N, E, l, R, r, NUM)
        
        # 更新计算周期统计
        computation_cycles = result * self.frequency
        self.stats.computation_cycles += computation_cycles
        
        # 更新乘法时间并返回
        self.asic.multiplytime += result
        return result

    def rescale_with_memory(self, N, E, l, R, r, NUM=1):
        """为rescale添加内存跟踪"""
        # 读取输入
        self.read_limb(N, l)
        
        # 跟踪ntt的内存
        t1 = self.ntt_with_memory(N, E, l, R, r, NUM*(r+1), inner=1)
        
        # 跟踪mod_down的内存
        t2 = self.mod_down_with_memory(N, E, l-1, R, r, NUM*(r+1))
        
        # 跟踪ntt的内存
        t3 = self.ntt_with_memory(N, E, l-1, R, r, NUM*(r+1), inner=1)
        
        # 写出输出
        self.write_limb(N, l-1)  # rescale后减少一个limb
        
        # 调用原始函数获取正确的时间
        result = self.asic.rescale(N, E, l, R, r, NUM)
        
        # 更新计算周期统计
        computation_cycles = result * self.frequency
        self.stats.computation_cycles += computation_cycles
        
        return result

    def rotate_with_memory(self, N, E, l, R, r, NUM=1):
        """为rotate添加内存跟踪"""
        # 读取输入和密钥
        self.read_limb(N, l)
        self.read_key(N, l+1)
        
        # 跟踪自同态内存操作
        for i in range(2):  # 密文中的两个多项式
            # 自同态操作
            poly_addr = f"auto_poly_{i}_{id(self)}"
            self.read_limb(N, l)
            self.write_limb(N, l)
        
        # 调用原始函数获取正确的时间
        result = self.asic.rotate(N, E, l, R, r, NUM)
        
        # 更新计算周期统计
        computation_cycles = result * self.frequency
        self.stats.computation_cycles += computation_cycles
        
        # 写出输出
        self.write_limb(N, l)
        
        # 更新rotate时间并返回
        self.asic.Rotatetime += result
        return result

    def keyswitch_with_memory(self, N, E, l, R, r, NUM=1):
        """为keyswitch添加内存跟踪"""
        # 读取输入和密钥
        self.read_limb(N, l)
        self.read_key(N, l+1)
        
        # 调用原始函数获取计算时间
        result = self.asic.keyswitch(N, E, l, R, r, NUM)
        
        # 更新计算周期统计
        computation_cycles = result * self.frequency
        self.stats.computation_cycles += computation_cycles
        
        # 写出输出
        self.write_limb(N, l)
        
        # 返回时间结果
        return result

    def get_memory_stats(self):
        """获取内存统计信息"""
        return self.stats

    def reset_stats(self):
        """重置内存统计信息"""
        self.stats = MemoryStats(max_cache_size=self.max_cache_size, cache_style=self.cache_style)
        self.cached_data = {}  # 清除缓存数据跟踪
        
        # 刷新并清空缓存
        if self.cache_style != CacheStyle.NONE:
            bytes_written = self.cache.clear()
            self.stats.dram_limb_wr += bytes_written