// macOS Vision 中文 OCR —— 课程 PPT 页面文字提取
// 编译：swiftc -O ocr_vision.swift -o ocr_vision
// 用法：./ocr_vision <图片> [zh-Hans,en-US]
// 输出：stdout 一行 JSON {file, lines:[{text,conf,x,y,w,h}]}，坐标已转成左上原点
//
// 为什么用它：本地、免费、不用联网、中文识别优于 tesseract、约 0.5s/页。
// 需要按位置剔除页眉页脚时，用返回的 y/h（0~1 归一化坐标）判断。

import AppKit
import Foundation
import Vision

let args = CommandLine.arguments
guard args.count > 1 else {
    FileHandle.standardError.write("usage: ocr_vision <image> [zh-Hans,en-US]\n".data(using: .utf8)!)
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
            "y": Double(1.0 - bb.origin.y - bb.size.height),  // 转成左上原点，方便按阅读顺序排
            "w": Double(bb.size.width),
            "h": Double(bb.size.height),
        ])
    }
}

// 按阅读顺序排序：先按 y 分行（容差 1.2%），再按 x
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
