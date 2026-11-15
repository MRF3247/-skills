import CoreText
import Foundation

// 用法: swift verify_fonts.swift [目录] [关键词...]
// 默认检查用户字体目录 + 输出匹配家族名；传目录则读取该目录文件并打印每个文件的真实家族名
// 注意: system_profiler SPFontsDataType 有缓存不可靠，CoreText 才是真相；家族名≠文件名

let args = CommandLine.arguments
if args.count >= 2 {
    // 模式2: 读取指定目录字体文件，打印真实家族名（用于确认「没匹配到」是否是家族名差异）
    let dir = URL(fileURLWithPath: args[1])
    let files = (try? FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil)) ?? []
    for f in files where ["ttf", "otf", "ttc"].contains(f.pathExtension.lowercased()) {
        let descs = CTFontManagerCreateFontDescriptorsFromURL(f as CFURL) as? [CTFontDescriptor] ?? []
        for d in descs {
            let name = CTFontDescriptorCopyAttribute(d, kCTFontFamilyNameAttribute) as? String ?? "?"
            print("\(f.lastPathComponent) -> \(name)")
        }
    }
} else {
    // 模式1: 查已注册家族
    let families = CTFontManagerCopyAvailableFontFamilyNames() as! [String]
    let checks = args.count > 2 ? Array(args[2...]) : []
    if checks.isEmpty {
        print("用法: swift verify_fonts.swift [目录] [关键词...]")
    } else {
        for k in checks {
            let hits = families.filter { $0.contains(k) }
            print("\(k): \(hits.isEmpty ? "未注册" : hits.joined(separator: "、"))")
        }
    }
}
