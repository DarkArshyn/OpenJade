// Bounded read-only search for graphics gamma calls and named gamma settings.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import java.nio.file.*;
import java.util.*;
public class OpenJadeColorState extends GhidraScript {
 public void run() throws Exception {
  if (!"6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9".equalsIgnoreCase(currentProgram.getExecutableSHA256())) throw new Exception("Hash mismatch");
  Path out=Paths.get(getScriptArgs()[0]); Files.createDirectory(out);
  Set<Function> functions=new LinkedHashSet<>(); StringBuilder log=new StringBuilder();
  var instructions=currentProgram.getListing().getInstructions(toAddr(0x00660000),true);
  while(instructions.hasNext()) {
   var ins=instructions.next(); if(ins.getAddress().getOffset()>=0x00670000)break;
   if(ins.getMnemonicString().equals("CALL") && (ins.toString().toLowerCase().contains("0x54") || ins.toString().toLowerCase().contains("0xe4") || ins.toString().toLowerCase().contains("0x114"))) {
    var f=getFunctionContaining(ins.getAddress());log.append(ins.getAddress()).append(" ").append(ins).append(" in ").append(f).append("\n");if(f!=null)functions.add(f);
   }
  }
  var data=currentProgram.getListing().getDefinedData(true);
  while(data.hasNext()) {
   var d=data.next(); Object value=d.getValue();
   if(value instanceof String && ((String)value).toLowerCase().contains("gamma")) {
    log.append(d.getAddress()).append(" ").append(value).append("\n");
    var refs=currentProgram.getReferenceManager().getReferencesTo(d.getAddress());
    while(refs.hasNext()){var ref=refs.next();var f=getFunctionContaining(ref.getFromAddress());log.append(ref).append(" ").append(f).append("\n");if(f!=null)functions.add(f);}
   }
  }
  functions.add(getFunctionAt(toAddr(0x00414380)));
  functions.add(getFunctionAt(toAddr(0x006633e0)));
  functions.add(getFunctionAt(toAddr(0x0072a190)));
  for(long address:new long[]{0x007a5930,0x007a5934,0x007a5938,0x007a5d80,0x007a8e4c,0x007afc3c}) log.append(Long.toHexString(address)).append(" float=").append(Float.intBitsToFloat(getInt(toAddr(address)))).append("\n");
  StringBuilder asm=new StringBuilder();var it=currentProgram.getListing().getInstructions(getFunctionAt(toAddr(0x006633e0)).getBody(),true);while(it.hasNext()){var i=it.next();asm.append(i.getAddress()).append(" ").append(i).append("\n");}Files.writeString(out.resolve("gamma-instructions.txt"),asm.toString());
  DecompInterface dec=new DecompInterface();dec.openProgram(currentProgram);
  try {for(Function f:functions){var r=dec.decompileFunction(f,60,monitor);if(r.decompileCompleted())Files.writeString(out.resolve(f.getEntryPoint()+".c"),r.getDecompiledFunction().getC());}}finally{dec.dispose();}
  Files.writeString(out.resolve("search.txt"),log.toString());
 }
}
