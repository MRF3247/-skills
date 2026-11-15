// 用 macOS Vision 框架做中文 OCR
// 编译：swiftc -O ocr_vision.swift -o ocr_vision
// 用法：./ocr_vision <图片> [lang]   → stdout 输出 JSON

import AppKit
import Foundation
import Vision

let args = CommandLine.arguments
guard args.count > 1 else {
    FileHandle.standardError.write("usage: ocr_vision <image> [zh-Hans|en-US]\n".data(using: .utf8)!)
    exit(2)
}
let path = args[1]
let langs = args.count > 2 ? args[2].split(separator: ",").map(String.init) : ["zh-Hans", "en-US"]

guard let image = NSImage(contentsOfFile: path),
      let tiff = image.tiffRepresentation,
      let rep = NSBitmapImageRep(data: tiff),
      let cg = rep.cgImage else {
    FileHandle.standardError.write("cannot read image: \(path)\n".data(using: .utf8)!)
    exit(1)
}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.recognitionLanguages = langs
request.usesLanguageCorrection = true
request.minimumTextHeight = 0.005

let handler = VNImageRequestHandler(cgImage: cg, options: [:])
do {
    try handler.perform([request])
} catch {
    FileHandle.standardError.write("vision error: \(error)\n".data(using: .utf8)!)
    exit(1)
}

var items: [[String: Any]] = []
if let observations = request.results {
    for obs in observations {
        guard let best = obs.topCandidates(1).first else { continue }
        let bb = obs.boundingBox
        items.append([
            "text": best.string,
            "conf": Double(best.confidence),
            "x": Double(bb.origin.x),
            "y": Double(1.0 - bb.origin.y - bb.size.height), // 转成左上原点
            "w": Double(bb.size.width),
            "h": Double(bb.size.height),
        ])
    }
}

// 按阅读顺序排序：先按 y 分行（容差），再按 x
items.sort { a, b in
    let ay = a["y"] as! Double, by = b["y"] as! Double
    if abs(ay - by) > 0.012 { return ay < by }
    return (a["x"] as! Double) < (b["x"] as! Double)
}

let out: [String: Any] = ["file": (path as NSString).lastPathComponent, "lines": items]
if let data = try? JSONSerialization.data(withJSONObject: out, options: [.withoutEscapingSlashes]),
   let s = String(data: data, encoding: .utf8) {
    print(s)
}
