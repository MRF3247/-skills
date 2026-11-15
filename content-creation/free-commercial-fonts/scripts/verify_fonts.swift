// CoreText 字体注册验证 — 比 system_profiler SPFontsDataType 可靠（后者有缓存，刚装完查不到≠没装上）
// 用法: swift verify_fonts.swift "LXGW" "Source Han" "Chill"   （默认查常用关键词）
// 注: CTFontManagerRegisterFontsForURL 返回 OSStatus -50 = 已注册（重复注册的正常信号）
import CoreText
import Foundation

let keywords = CommandLine.arguments.count > 1
    ? Array(CommandLine.arguments.dropFirst())
    : ["LXGW", "Source Han", "Smiley", "Alibaba", "Zhuque", "Xiaolai", "Yozai",
       "MiSans", "OPPO", "Fira", "JetBrains", "Maple", "Ark Pixel", "Inter",
       "Maoken", "Chill", "FengYa", "Yuanmo"]
let families = CTFontManagerCopyAvailableFontFamilyNames() as! [String]
for k in keywords {
    let hits = families.filter { $0.contains(k) }
    print("\(k): \(hits.isEmpty ? "未注册" : hits.joined(separator: "、"))")
}
